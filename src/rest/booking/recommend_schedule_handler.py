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
import datetime as dt
import booking_constant as BC
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, User, UserAddress, UserDefaultAddress
from data.dao.userdao import UserDAO 
from data.dao.addressdao import AddressDAO
from data.dao.masterdao import MasterDAO
from utils.datetime_utils import time_to_str
from response import Response
from data.intermediate.value_holder import IntermediateValueHolder
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel

class ScheduleRecommendHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")

        uid                 = self.get_argument('uid', '')
        taking_time         = self.get_argument('taking_time', 25)
        additional_time     = self.get_argument('additional_time', 10)
        appointment_type    = self.get_argument('appointment_type', 0)
        have_pet            = self.get_argument('have_pet', 0)
        master_gender       = self.get_argument('master_gender', 0)
        isdirty             = self.get_argument('isdirty', 0)

        # convert
        appointment_type        = int(appointment_type)
        have_pet                = int(have_pet)

        taking_time             = int(taking_time)
        additional_time         = int(additional_time)
        taking_time_in_minutes        = taking_time * 6 
        additional_time_in_minutes    = additional_time * 6 
        total_taking_time_in_minutes  = taking_time_in_minutes + additional_time_in_minutes


        master_gender           = int(master_gender) # 0 dont care 1 women 2 men
        isdirty                 = int(isdirty)

        ret = {}

        print 'recommend schedule'
        print 'taking time :', taking_time_in_minutes

        mongo_logger = get_mongo_logger()

        mongo_logger.debug('%s request recommendation' % uid, extra = {'taking_time' : taking_time, 
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

            start_time_range_begin = 8
            start_time_range_end = 18

            # 똥집인 경우 3시간 추가됨.
            if isdirty == 1:
                if appointment_type == BC.ONE_TIME or appointment_type == BC.ONE_TIME_BUT_CONSIDERING:
                    total_taking_time_in_minutes += 120


            #get available homemaster's time table day by day
            schedule_by_date_list = masterdao.get_recommended_schedule(gu_id, have_pet, master_gender, appointment_type, geohash6, dt.datetime.now().date())
            success, msg, store_key, search_keys, result = masterdao.find_master_by_score(schedule_by_date_list, \
                                                gu_id, \
                                                uid, \
                                                appointment_type, \
                                                None, \
                                                start_time_range_begin, \
                                                0,
                                                start_time_range_end, \
                                                0,
                                                total_taking_time_in_minutes, \
                                                geohash6, 
                                                True)

            # if not successful
            if success != 'SUCCESS':
                print 'haha no recommendation.....'
                self.set_status(Response.RESULT_OK)
                ret['response'] = 'NoRecommendation'
                mongo_logger.error('have no recommendation', extra = {'err' : msg})
                #add_err_message_to_response(ret, err_dict['err_hm_no_recommendation'])
                #self.write(json.dumps(ret))
                return 
            else:
                schedules = []

                for row in result:
                    s = {}
                    s['date']       = row['date']
                    s['start_time'] = time_to_str(row['start_time'])
                    s['end_time']   = time_to_str(row['end_time'])

                    schedules.append(s)

                # 스케쥴이 이미 해당 날짜에 있다면, 있다고 표시하고 리턴함
                num_schedules_on_dates = userdao.get_user_schedule_on_dates(uid, [dt.datetime.strptime(str(s['date']), '%Y%m%d').date() for s in schedules])
                if num_schedules_on_dates > 0:
                    print 'already have appointment on that days, no recommendation.....'

                    holder.remove(store_key)
                    for sk in search_keys:
                        holder.remove(sk)
                    
                    self.set_status(Response.RESULT_OK)
                    ret['response'] = 'NoRecommendation'
                    mongo_logger.error('have no recommendation', extra = {'err' : 'already have cleaning on that day'})
                    #add_err_message_to_response(ret, err_dict['err_hm_no_recommendation'])
                    #self.write(json.dumps(ret))
                    return 

                mid = row['mid']
                name, img_url, avg_rating = masterdao.get_master_name_img_and_average_rating(mid)

                search_keys_str = ','.join(search_keys)
                print 'search key string :', search_keys_str
                ret['response'] = {'store_key' : store_key, 'search_keys' : search_keys_str, 'schedules' : schedules, 'uid' : uid, 'mid' : row['mid'], 'name' : name, 'img_url' : img_url, 'avg_rating' : str(float(avg_rating))}

                mix.track(uid, 'recommend', {'time' : dt.datetime.now(), 'master_gender' : master_gender})
                mongo_logger.debug('%s got recommendation' % uid, extra = {'user_id' : uid})
                
                self.set_status(Response.RESULT_OK)

                print uid, 'got recommendation '

                self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
            mongo_logger.error('error occurred when make recommendation', extra = {'err' : str(e)})

            # if error occur, then remove all keys
            holder.remove(store_key)
            for sk in search_keys:
                holder.remove(sk)
        finally:
            session.close()
            self.write(json.dumps(ret))


