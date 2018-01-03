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
from hashids import Hashids
from schedule.schedule_helper import HMScheduler
from sqlalchemy import func, or_, and_
from nptime import nptime
from utils.datetime_utils import time_to_str, timedelta_to_time, time_to_minutes
from utils.geo_utils import get_moving_time
from data.session.mysql_session import engine, Session
from data.intermediate.value_holder import IntermediateValueHolder
from data.model.data_model import UserPaymentRecord, Booking, UserDefaultAddress, UserDefaultCard
from data.dao.userdao import UserDAO
from data.dao.addressdao import AddressDAO
from data.dao.masterdao import MasterDAO
from err.error_handler import print_err_detail, err_dict
from response import Response
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from data.intermediate.value_holder import IntermediateValueHolder
from response import add_err_message_to_response, add_err_ko_message_to_response
from sqlalchemy.exc import IntegrityError
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel
from sender.alimtalk_sender import send_alimtalk
from sender.push_sender import send_booking_schedule_updated
from utils.datetime_utils import convert_datetime_format2
try:
    from utils.secrets import MANAGERS_CALL
except ImportError:
    MANAGERS_CALL = ''


class ChangeCircleHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        print "call change_circle_handler"

        ret = {}

        org_booking_id                  = self.get_argument('booking_id', '')

        new_booking_date                = self.get_argument('date', dt.datetime.strftime(dt.datetime.now(), '%Y%m%d'))
        new_booking_time                = self.get_argument('time', '08:00')
        master_ids                      = self.get_argument('master_ids', [])
        new_appointment_type            = self.get_argument('appointment_type', '')

        # convert parameters
        selected_date_str               = new_booking_date
        time_str                        = new_booking_time
        new_booking_date                = dt.datetime.strptime(new_booking_date, '%Y%m%d')
        master_ids                      = master_ids.split(',')
        new_appointment_type            = int(new_appointment_type)

        # logging part
        mix = get_mixpanel()
        mongo_logger = get_mongo_logger()

        print 'change circle'
        print selected_date_str, time_str
        print '*' * 100

        try:
            session = Session()
            try:
                row = session.query(Booking).filter(Booking.id == org_booking_id).one()
            except NoResultFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_no_record'])
                return

            except MultipleResultsFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_multiple_record'])
                return


            org_request_id              = row.request_id
            org_appointment_index       = row.appointment_index
            org_additional_task         = row.additional_task
            org_master_id               = row.master_id
            org_start_time              = row.start_time
            org_estimated_end_time      = row.estimated_end_time
            user_id                     = row.user_id
            card_idx                    = row.card_idx
            addr_idx                    = row.addr_idx
            havetools                   = row.havetools
            have_pet                    = row.havepet
            isdirty                     = row.is_dirty
            master_gender               = row.master_gender
            cleaning_duration           = row.cleaning_duration
            #payment_status          = BC.BOOKING_UNPAID_YET

            # 원래 예약된 정보 불러오기
            all_bookings = session.query(Booking) \
                                  .filter(Booking.request_id == org_request_id) \
                                  .filter(Booking.appointment_index >= org_appointment_index) \
                                  .filter(Booking.cleaning_status > BC.BOOKING_CANCELED) \
                                  .order_by(Booking.start_time) \
                                  .all()
            # 예약된 정보의 상태 변경
            for booking in all_bookings:
                print "change cleanning_status"
                booking.cleaning_status = BC.BOOKING_CANCELED
                # 결제 상태에 따른 상태 변경
            session.commit()

            # 주기에 따른 예약 생성
            # request id to group each individual bookings
            request_id = str(uuid.uuid4())
            # hasids to generate unique booking id
            now = dt.datetime.strftime(dt.datetime.now(), '%Y%m%d%H%M%S')
            hashids = Hashids(min_length = 16, salt = now + user_id)

            userdao     = UserDAO()
            masterdao   = MasterDAO()
            holder      = IntermediateValueHolder()

            cal_appointment_type = new_appointment_type
            count_of_iteration = cal_appointment_type * 2 + 1 # 2 months

            date_list = []

            week_const = 4 / cal_appointment_type

            for i in xrange(count_of_iteration):
                date = new_booking_date + dt.timedelta(weeks = week_const * i)
                date = dt.datetime.strftime(date, '%Y%m%d')
                date_list.append(date)

            print "date_list : ", date_list

            master_num = len(master_ids)

            i = 0
            booking_info = {}
            time = new_booking_time

            house_type, size = userdao.get_user_house_type_size(org_booking_id)
            print "house_type : ", house_type
            print "size : ", size

            while i < master_num:
                mid = master_ids[i]
                master_date_keys = []

                name, img_url, avg_rating = masterdao.get_master_name_img_and_average_rating(mid)

                print "master_name : ", name
                print "img_url : ", img_url
                print "avg_rating : ", avg_rating

                for date in date_list:
                    key = '%s_%s' % (mid, date)
                    master_date_keys.append(key)

                print "master_date_keys : ", master_date_keys

                booking_item_key = '%s_%s_%d' % (user_id, master_date_keys[0], new_appointment_type)
                #if holder.store_keys(master_date_keys) and not masterdao.is_master_off_date(mid, new_booking_date.date()): # 메모리에 키가 하나도 없을 때, 즉 예약이 가능할 때
                #    holder.store(booking_item_key, booking_info)

                new_appointment_idx = 1;

                for date in date_list:
                    print date, time
                    booking_id = hashids.encode(int(date + time.replace(':', '')))
                    print 'new_booking_id : ', booking_id
                    date       = dt.datetime.strptime(date, '%Y%m%d')
                    dow        = date.date().weekday()
                    booking_time       = dt.time(hour = int(time.split(':')[0]), minute = int(time.split(':')[1]))
                    start_time         = dt.datetime.combine(date, booking_time)
                    estimated_end_time = start_time # + dt.timedelta(minute = )
                    print "booking_time : ", booking_time
                    print "start_time : ", start_time
                    print "estimated_end_time : ", estimated_end_time
                i += 1

            '''while i < master_num:
                mid = master_ids[i]
                master_date_keys = []

                name, img_url, avg_rating = masterdao.get_master_name_img_and_average_rating(mid)

                for date in date_list:
                    key = '%s_%s' % (mid, date)
                    master_date_keys.append(key)

                booking_item_key = '%s_%s_%d' % (uid, master_date_keys[0], appointment_type)

                # 가능 일정을 미리 호출한 고객과, 그 바로 직후 휴무 신청을 한 홈마스터의 경우, 예약이 불가 하기 때문에 체크하도록 함
                if holder.store_keys(master_date_keys) and not masterdao.is_master_off_date(mid, selected_date.date()): # 메모리에 키가 하나도 없을 때, 즉 예약이 가능할 때
                    holder.store(booking_item_key, booking_info)

                    new_appointment_idx = 1;
                    for date in date_list:
                        print date, time
                        booking_id = hashids.encode(int(date + time.replace(':', '')))
                        dow        = date.date().weekday()

                        print 'key', booking_id
                        booking_time       = dt.time(hour = int(time.split(':')[0]), minute = int(time.split(':')[1]))
                        start_time         = dt.datetime.combine(date, booking_time)
                        estimated_end_time = estimated_end_time - dt.timedelta(minutes = additional_time + first_added_time)

                        booking = Booking(id = booking_id,
                                          request_id = request_id,
                                          user_id = uid,
                                          master_id = mid,
                                          appointment_type = new_appointment_type,
                                          appointment_index = new_appointment_idx,
                                          dow = dow,
                                          booking_time = dt.datetime.now(),
                                          org_start_time = start_time,
                                          start_time = start_time,
                                          estimated_end_time = estimated_end_time,
                                          end_time = estimated_end_time, # update after homemaster finish their job
                                          cleaning_duration = cleaning_duration,
                                          additional_task = additional_task,
                                          price = price,
                                          price_with_task = actual_price,
                                          charging_price = 0,
                                          card_idx = card_idx,
                                          addr_idx = addr_idx,
                                          havetools = havetools,
                                          havepet = have_pet,
                                          laundry_apply_all = laundry_apply_all,
                                          is_dirty = isdirty,
                                          master_gender = master_gender,
                                          status = BC.BOOKING_UPCOMMING,
                                          cleaning_status = BC.BOOKING_UPCOMMING,
                                          payment_status = BC.BOOKING_UNPAID_YET)

                    #booking_info['search_keys'] = master_date_keys
                    #booking_info['store_key']   = booking_item_key
                    return
                i += 1'''





            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)
        except Exception, e:
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)
            mongo_logger.error('error request update schedules', extra = {'user_id' : user_id, 'err' : str(e)})

        finally:
            session.close()
            self.write(json.dumps(ret))
