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


class RequestSelectScheduleHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        ret = {}

        uid                         = self.get_argument('uid', '')
        appointment_type            = self.get_argument('appointment_type', BC.ONE_TIME)
        additional_task             = self.get_argument('additional_task', 0)
        temp_additional_task        = self.get_argument('addtional_task', 0) # deal with typo
        date                        = self.get_argument('date', dt.datetime.strftime(dt.datetime.now(), '%Y%m%d'))
        time                        = self.get_argument('time', '08:00')
        taking_time                 = self.get_argument('taking_time', 25)
        first_added_time            = self.get_argument('first_added_time', 0)
        additional_time             = self.get_argument('additional_time', 10)
        have_pet                    = self.get_argument('have_pet', 0)
        master_gender               = self.get_argument('master_gender', 0)
        isdirty                     = self.get_argument('isdirty', 0)
        master_ids                  = self.get_argument('master_ids', [])

        # convert parameters
        selected_date_str           = date
        selected_date               = dt.datetime.strptime(date, '%Y%m%d')
        master_ids                  = master_ids.split(',')

        appointment_type                = int(appointment_type)
        additional_task                 = int(additional_task)
        taking_time                     = int(taking_time)
        first_added_time                = int(first_added_time)
        additional_time                 = int(additional_time)

        have_pet                        = int(have_pet)
        master_gender                   = int(master_gender) # 0 dont care 1 women
        isdirty                         = int(isdirty)

        print temp_additional_task, type(temp_additional_task)
        print additional_task, type(additional_task)
        if temp_additional_task > 0: # ios typo bug temporary fix
            additional_task = str(temp_additional_task)
            additional_task = int(additional_task, 2)
            if additional_task >= 64:
                additional_task -= 64


        if additional_task > 64: # ios typo bug temporary fix
            additional_task = str(additional_task)
            additional_task = int(additional_task, 2)
            if additional_task >= 64:
                additional_task -= 64


        taking_time_in_minutes          = taking_time * 6
        first_added_time_in_minutes     = first_added_time * 6
        additional_time_in_minutes      = additional_time * 6
        total_taking_time_in_minutes    = taking_time_in_minutes + first_added_time_in_minutes + additional_time_in_minutes

        print '*' * 50
        print additional_task
        print '*' * 50

        if isdirty == 1:
            total_taking_time_in_minutes += 120

        # logging part
        mix = get_mixpanel()
        mongo_logger = get_mongo_logger()

        try:
            booking_info = {}

            masterdao   = MasterDAO()
            holder      = IntermediateValueHolder()

            cal_appointment_type = appointment_type

            if cal_appointment_type == BC.ONE_TIME_BUT_CONSIDERING:
                cal_appointment_type = BC.ONE_TIME

            count_of_iteration = cal_appointment_type * 2 + 1 # 2 months

            date_list = []

            if cal_appointment_type == BC.ONE_TIME:
                week_const = 0
            else:
                week_const = 4 / cal_appointment_type

            for i in xrange(count_of_iteration):
                date = selected_date + dt.timedelta(weeks = week_const * i)
                date = dt.datetime.strftime(date, '%Y%m%d')
                date_list.append(date)

            booking_info['dates']            = date_list
            booking_info['time']             = time
            booking_info['appointment_type'] = appointment_type
            booking_info['additional_task']  = additional_task
            booking_info['have_pet']         = have_pet
            booking_info['master_gender']    = master_gender
            booking_info['isdirty']          = isdirty
            booking_info['user_id']          = uid
            booking_info['taking_time']      = taking_time_in_minutes
            booking_info['first_added_time'] = first_added_time_in_minutes
            booking_info['additional_time']  = additional_time_in_minutes
            booking_info['total_time']       = total_taking_time_in_minutes

            # 각 마스터별로 예약이 가능한지 메모리에서 다시 한번 확인.
            # 선택한 값을 메모리에 키로 저장하여 중복되는 예약 방지.
            # 선택 했으면 선택된 정보를 가지고 있어야 함
            master_num = len(master_ids)

            i = 0
            while i < master_num: # 랭킹이 높은 홈마스터별로 확인
                mid = master_ids[i]
                if not masterdao.is_valid_master(mid):
                    self.set_status(Response.RESULT_OK)
                    add_err_message_to_response(ret, err_dict['err_not_valid_master'])
                    return

                master_date_keys = []

                name, img_url, avg_rating   = masterdao.get_master_name_img_and_average_rating(mid)
                booking_info['master_id']   = mid
                booking_info['name']        = name
                booking_info['img_url']     = img_url
                booking_info['avg_rating']  = avg_rating

                # 날짜별 키 생성
                for date in date_list:
                    key = '%s_%s' % (mid, date)
                    master_date_keys.append(key)

                # 저장할 키 생성
                booking_item_key = '%s_%s_%d' % (uid, master_date_keys[0], appointment_type)

                # 가능 일정을 미리 호출한 고객과, 그 바로 직후 휴무 신청을 한 홈마스터의 경우, 예약이 불가 하기 때문에 체크하도록 함
                if holder.store_keys(master_date_keys) and not masterdao.is_master_off_date(mid, selected_date.date()): # 메모리에 키가 하나도 없을 때, 즉 예약이 가능할 때
                    holder.store(booking_item_key, booking_info)

                    master_date_keys = ','.join(master_date_keys)

                    booking_info['search_keys'] = master_date_keys
                    booking_info['store_key']   = booking_item_key

                    ret['response'] = booking_info

                    self.set_status(Response.RESULT_OK)

                    # log to mixpanel
                    mix.track(uid, 'select schedule', {'time' : dt.datetime.now(), 'user_id' : uid, 'master_id' : mid, 'sel_date' : selected_date_str, 'sel_time' : time, 'taking_time' : taking_time, 'additional_time' : additional_time, 'appointment_type' : appointment_type, 'have_pet' : have_pet, 'master_gender' : master_gender,'isdirty' : isdirty})

                    # log to mongo
                    mongo_logger.debug('select schedule', extra = {'log_time' : dt.datetime.now(), 'user_id' : uid, 'master_id' : mid, 'sel_date' : selected_date_str, 'sel_time' : time, 'taking_time' : taking_time, 'additional_time' : additional_time, 'appointment_type' : appointment_type, 'have_pet' : have_pet, 'master_gender' : master_gender,'isdirty' : isdirty})
                    return

                i += 1

            # when not available

            # log to mixpanel
            mix.track(uid, 'cannot select schedule', {'time' : dt.datetime.now(), 'user_id' : uid, 'sel_date' : selected_date_str, 'sel_time' : time, 'taking_time' : taking_time, 'additional_time' : additional_time, 'appointment_type' : appointment_type, 'have_pet' : have_pet, 'master_gender' : master_gender,'isdirty' : isdirty})

            # log to mongo
            mongo_logger.debug('cannot select schedule', extra = {'user_id' : uid, 'sel_date' : selected_date_str, 'sel_time' : time, 'taking_time' : taking_time, 'additional_time' : additional_time, 'appointment_type' : appointment_type, 'have_pet' : have_pet, 'master_gender' : master_gender,'isdirty' : isdirty})

            # other users preempt homemasters, so no homemaster available
            self.set_status(Response.RESULT_OK)
            add_err_message_to_response(ret, err_dict['err_homemaster_occupied'])
            return

        except Exception, e:
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)
            mongo_logger.error('error request select schedules', extra = {'user_id' : uid, 'err' : str(e)})

        finally:
            self.write(json.dumps(ret))
