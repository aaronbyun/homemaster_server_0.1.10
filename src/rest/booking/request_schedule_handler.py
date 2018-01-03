#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import json
import tornado.ioloop
import tornado.web
import uuid
import requests
import pickle
import datetime as dt
import booking_constant as BC
from utils.datetime_utils import time_to_str
from data.session.mysql_session import engine, Session
from data.intermediate.value_holder import IntermediateValueHolder
from data.model.data_model import UserPaymentRecord, Booking, UserDefaultAddress, UserDefaultCard
from data.dao.userdao import UserDAO 
from data.dao.addressdao import AddressDAO
from data.dao.masterdao import MasterDAO
from err.error_handler import print_err_detail, err_dict
from response import Response
from data.intermediate.value_holder import IntermediateValueHolder
from response import add_err_message_to_response, add_err_ko_message_to_response
from sqlalchemy.exc import IntegrityError
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel

class RequestScheduleHandler(tornado.web.RequestHandler):
    def post(self):
            self.set_header("Content-Type", "application/json")

            ret = {}

            uid                         = self.get_argument('uid', '')
            date                        = self.get_argument('date', dt.datetime.now())
            start_time_range_begin      = self.get_argument('range_begin', BC.START_TIME_RANGE_BEGIN)
            start_time_range_begin_min  = self.get_argument('range_begin_min', 0)
            start_time_range_end        = self.get_argument('range_end',   BC.START_TIME_RANGE_END)
            start_time_range_end_min    = self.get_argument('range_end_min',   0)
            appointment_type            = self.get_argument('appointment_type', BC.ONE_TIME)
            taking_time                 = self.get_argument('taking_time', 25)
            first_added_time            = self.get_argument('first_added_time', 0)
            additional_time             = self.get_argument('additional_time', 10)
            have_pet                    = self.get_argument('have_pet', 0)
            master_gender               = self.get_argument('master_gender', 0)
            isdirty                     = self.get_argument('isdirty', 0)

            # convert datetime
            date                    = dt.datetime.strptime(date, '%Y%m%d')

            start_time_range_begin      = int(start_time_range_begin)
            start_time_range_begin_min  = int(start_time_range_begin_min)

            start_time_range_end        = int(start_time_range_end)
            start_time_range_end_min    = int(start_time_range_end_min)

            appointment_type        = int(appointment_type)
            taking_time             = int(taking_time)
            first_added_time        = int(first_added_time)
            additional_time         = int(additional_time)
            
            taking_time_in_minutes        = taking_time * 6 
            first_added_time_in_minutes   = first_added_time * 6
            additional_time_in_minutes    = additional_time * 6 
            total_taking_time_in_minutes  = taking_time_in_minutes + first_added_time_in_minutes + additional_time_in_minutes

            have_pet                = int(have_pet)
            master_gender           = int(master_gender) # 0 dont care 1 women 2 men
            isdirty                 = int(isdirty)

            print 'request schedule'
            print 'taking time :', taking_time_in_minutes

            mongo_logger = get_mongo_logger()

            mongo_logger.debug('%s request schedule' % uid, extra = { 'date' : dt.datetime.strftime(date, '%Y%m%d'),
                                                                      'start_time_range_begin' : start_time_range_begin,
                                                                      'start_time_range_end' : start_time_range_end,
                                                                        'taking_time' : taking_time, 
                                                                        'additional_time' : additional_time, 
                                                                        'appointment_type' : appointment_type, 
                                                                        'have_pet' : have_pet, 'master_gender' : master_gender,
                                                                        'isdirty' : isdirty})

            
            mix = get_mixpanel()

            try:
                session = Session()

                userdao = UserDAO()
                addrdao = AddressDAO()
                masterdao = MasterDAO()

                holder = IntermediateValueHolder()

                # request id to group each individual bookings
                request_id = str(uuid.uuid4())

                # get user's address and cover address to gu code
                address, geohash5, geohash6 = userdao.get_user_address(uid)
                gu_id = addrdao.get_gu_id(address)

                # four consecutive appointment days to make booking if regular , otherwise just one day
                dates = [int(dt.datetime.strftime(date, '%Y%m%d'))]

                if appointment_type == BC.ONE_TIME_A_MONTH or appointment_type == BC.TWO_TIME_A_MONTH or appointment_type == BC.FOUR_TIME_A_MONTH:
                    dates = [int(dt.datetime.strftime(date + dt.timedelta(days = i * BC.DAYS_IN_A_WEEK * (4 / appointment_type)), '%Y%m%d'))  for i in xrange(4)]


                # 크리스마스 및 새해 임시로 막음.
                if date.date() == dt.date(2016, 2, 7) or date.date() == dt.date(2016, 2, 8) or date.date() == dt.date(2016, 2, 9) or date.date() == dt.date(2016, 2, 10):
                    self.set_status(Response.RESULT_OK)
                    add_err_ko_message_to_response(ret, '설날 연휴동안은, 예약이 불가능합니다.')
                    self.write(json.dumps(ret))
                    return 

                # 스케쥴이 이미 해당 날짜에 있다면, 있다고 표시하고 리턴함
                num_schedules_on_dates = userdao.get_user_schedule_on_dates(uid, [dt.datetime.strptime(str(d), '%Y%m%d').date() for d in dates])
                if num_schedules_on_dates > 0:
                    self.set_status(Response.RESULT_OK)
                    add_err_message_to_response(ret, err_dict['err_schedules_on_dates'])
                    self.write(json.dumps(ret))
                    return 

                # 똥집인 경우 3시간 추가됨.
                if isdirty == 1:
                    if appointment_type == BC.ONE_TIME or appointment_type == BC.ONE_TIME_BUT_CONSIDERING:
                        total_taking_time_in_minutes += 120

                print 'gu_id', gu_id, have_pet, master_gender, dates

                #get available homemaster's time table day by day
                schedule_by_date_list = masterdao.get_master_schedule_by_dates(gu_id,have_pet, master_gender, dates)
                success, msg, store_key, search_keys, result = masterdao.find_master_by_score(schedule_by_date_list, \
                                                    gu_id, \
                                                    uid, \
                                                    appointment_type, \
                                                    dates, \
                                                    start_time_range_begin, \
                                                    start_time_range_begin_min, \
                                                    start_time_range_end, \
                                                    start_time_range_end_min, \
                                                    total_taking_time_in_minutes, \
                                                    geohash6)

                # if not successful
                if success != 'SUCCESS':
                    self.set_status(Response.RESULT_OK)
                    add_err_message_to_response(ret, err_dict['err_no_hm_at_that_time'])
                    mix.track(uid, 'request schedule', {'time' : dt.datetime.now(), 'date' : dt.datetime.strftime(date, '%Y%m%d'),
                                                                      'start_time_range_begin' : start_time_range_begin,
                                                                      'start_time_range_begin_min' : start_time_range_begin_min,
                                                                      'start_time_range_end' : start_time_range_end,
                                                                      'start_time_range_end_min' : start_time_range_end_min,
                                                                        'taking_time' : taking_time, 
                                                                        'additional_time' : additional_time, 
                                                                        'appointment_type' : appointment_type, 
                                                                        'have_pet' : have_pet, 'master_gender' : master_gender,
                                                                        'isdirty' : isdirty, 'status' : 'no homemaster'})
                    print uid, 'was not able to find any homemasters....'
                else:
                    schedules = []

                    for row in result:
                        s = {}
                        s['date']       = row['date']
                        s['start_time'] = time_to_str(row['start_time'])
                        s['end_time']   = time_to_str(row['end_time'])

                        schedules.append(s)

                    mid = row['mid']
                    name, img_url, avg_rating = masterdao.get_master_name_img_and_average_rating(mid)

                    search_keys_str = ','.join(search_keys)
                    ret['response'] = {'store_key' : store_key, 'search_keys' : search_keys_str, 'schedules' : schedules, 'uid' : uid, 'mid' : row['mid'], 'name' : name, 'img_url' : img_url, 'avg_rating' : str(float(avg_rating))}
                    print uid, 'successfully made booking requests...'

                    mix.track(uid, 'request schedule', {'time' : dt.datetime.now(), 'date' : dt.datetime.strftime(date, '%Y%m%d'),
                                                                      'start_time_range_begin' : start_time_range_begin,
                                                                      'start_time_range_begin_min' : start_time_range_begin_min,
                                                                      'start_time_range_end' : start_time_range_end,
                                                                      'start_time_range_end_min' : start_time_range_end_min,
                                                                        'taking_time' : taking_time, 
                                                                        'additional_time' : additional_time, 
                                                                        'appointment_type' : appointment_type, 
                                                                        'have_pet' : have_pet, 'master_gender' : master_gender,
                                                                        'isdirty' : isdirty, 'status' : 'find homemaster'})
                    mongo_logger.debug('%s made booking requests' % uid, extra = {'user_id' : uid})
                    
                self.set_status(Response.RESULT_OK)
                
            except Exception, e:
                session.rollback()
                add_err_message_to_response(ret, err_dict['err_mysql'])
                self.set_status(Response.RESULT_SERVERERROR)
                print_err_detail(e)
                mongo_logger.error('error occurred when request schedule', extra = {'err' : str(e)})


                # if error occur, then remove all keys
                holder.remove(store_key)
                for sk in search_keys:
                    holder.remove(sk)

            finally:
                session.close()
                self.write(json.dumps(ret))
