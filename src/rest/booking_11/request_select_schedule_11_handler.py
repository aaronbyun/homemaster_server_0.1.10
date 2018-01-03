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
import booking.booking_constant as BC
from hashids import Hashids
from schedule.schedule_helper import HMScheduler
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
from data.intermediate.value_holder import IntermediateValueHolder
from response import add_err_message_to_response, add_err_ko_message_to_response
from sqlalchemy.exc import IntegrityError
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel
from utils.time_price_info import get_time_price, get_additional_task_time_price

try:
    from utils.secrets import API_11ST_KEY
except ImportError:
    API_11ST_KEY = ''


class RequestSelectSchedule11stHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        date                        = self.get_argument('date', dt.datetime.strftime(dt.datetime.now(), '%Y%m%d'))
        time                        = self.get_argument('start_time', '08:00')
        master_ids                  = self.get_argument('master_ids', [])
        comb_key                    = self.get_argument('comb_key', '')

        # convert parameters
        selected_date_str           = date
        selected_date               = dt.datetime.strptime(date, '%Y%m%d')
        master_ids                  = master_ids.split(',')

        keys = comb_key.split('_')

        # logging part
        mix = get_mixpanel()
        mongo_logger = get_mongo_logger()

        try:
            booking_info = {}

            masterdao   = MasterDAO()
            holder      = IntermediateValueHolder()

            print comb_key
            appointment_type = int(comb_key.split('_')[2])

            date_list = []

            if appointment_type == BC.ONE_TIME:
                count_of_iteration = 1
                week_const = 0
            else:
                count_of_iteration = appointment_type * 2 # 2 months
                week_const = 4 / appointment_type

            for i in xrange(count_of_iteration):
                date = selected_date + dt.timedelta(weeks = week_const * i)
                date = dt.datetime.strftime(date, '%Y%m%d')
                date_list.append(date)

            booking_info['dates']             = date_list
            booking_info['time']              = time
            booking_info['comb_key']          = comb_key

            house_type       = comb_key.split('_')[0]
            if house_type == 'officetel':
                house_type = 0
            elif house_type == 'rowhouse':
                house_type = 1
            else:
                house_type = 2

            house_type       = int(house_type)
            house_size       = int(comb_key.split('_')[1])
            additional_task  = int(comb_key.split('_')[3])

            print comb_key
            print appointment_type, house_type, house_size
            _, cleaning_duration, _, _ = get_time_price(appointment_type, house_type, house_size)
            booking_info['cleaning_duration'] = cleaning_duration

            task_time, _ = get_additional_task_time_price(additional_task, house_type, house_size)
            booking_info['additional_time'] = task_time
            print task_time

            # 각 마스터별로 예약이 가능한지 메모리에서 다시 한번 확인.
            # 선택한 값을 메모리에 키로 저장하여 중복되는 예약 방지.
            # 선택 했으면 선택된 정보를 가지고 있어야 함
            master_num = len(master_ids)

            i = 0
            while i < master_num: # 랭킹이 높은 홈마스터별로 확인
                mid = master_ids[i]
                master_date_keys = []

                name, img_url, avg_rating   = masterdao.get_master_name_img_and_average_rating(mid)
                booking_info['master_id']   = mid
                booking_info['name']        = name
                booking_info['img_url']     = img_url
                booking_info['avg_rating']  = avg_rating

                now = dt.datetime.strftime(dt.datetime.now(), '%Y%m%d%H%M%S')
                hashids = Hashids(min_length = 16, salt = now + comb_key)
                booking_id = hashids.encode(int(date + time.replace(':', '')))
                booking_info['id']  = booking_id

                # 날짜별 키 생성
                for date in date_list:
                    key = '%s_%s' % (mid, date)
                    master_date_keys.append(key)

                # 저장할 키 생성
                #booking_item_key = '%s_%s' % (comb_key, master_date_keys[0])

                if holder.store_keys(master_date_keys, source = '11st') and not masterdao.is_master_off_date(mid, selected_date.date()): # 메모리에 키가 하나도 없을 때, 즉 예약이 가능할 때
                    master_date_keys = ','.join(master_date_keys)
                    booking_info['search_keys'] = master_date_keys
                    booking_info['store_key']   = booking_id  # 11번가의 경우는, 미리 생성한 아이디 키로 한다.

                    holder.store(booking_id, booking_info, source = '11st')

                    # for 11st response
                    ret['response'] = {'booking_available' : 'Y', 'booking_id' : booking_id}

                    self.set_status(Response.RESULT_OK)

                    # log to mixpanel
                    #mix.track(uid, '11 select schedule', {'time' : dt.datetime.now(), 'user_id' : uid, 'master_id' : mid, 'sel_date' : selected_date_str, 'sel_time' : time, 'taking_time' : taking_time, 'additional_time' : additional_time, 'appointment_type' : appointment_type, 'have_pet' : have_pet, 'master_gender' : master_gender,'isdirty' : isdirty})

                    # log to mongo
                    mongo_logger.debug('11 select schedule', extra = {'master_id' : mid, 'sel_date' : selected_date_str, 'sel_time' : time, 'comb_key' : comb_key})
                    return

                i += 1

            # when not available
            # log to mongo
            mongo_logger.debug('11 cannot select schedule', extra = {'sel_date' : selected_date_str, 'sel_time' : time, 'comb_key' : comb_key})

            # other users preempt homemasters, so no homemaster available
            self.set_status(Response.RESULT_OK)

            ret['response'] = {'booking_available' : 'N'}

            return

        except Exception, e:
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)
            mongo_logger.error('error 11 request select schedules', extra = {'err' : str(e)})

        finally:
            self.write(json.dumps(ret))
