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
import rest.booking.booking_constant as BC
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
from utils.geo_utils import get_latlng_from_address, get_geohash
from utils.time_price_info import get_time_price, get_additional_task_time_price


class RequestAvailableSchedules11stHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        address                     = self.get_argument('address', '')
        house_type                  = self.get_argument('house_type', 0)
        house_size                  = self.get_argument('house_size', 10)

        appointment_type            = self.get_argument('appointment_type', BC.ONE_TIME)
        additional_task             = self.get_argument('additional_task', 0)
        have_pet                    = self.get_argument('have_pet', 0)
        master_gender               = self.get_argument('master_gender', 0)
        isdirty                     = self.get_argument('isdirty', 0)

        # convert parameters
        house_type                      = int(house_type)
        house_size                      = int(house_size)
        appointment_type                = int(appointment_type)
        additional_task                 = int(additional_task)
        have_pet                        = int(have_pet)
        master_gender                   = int(master_gender) # 0 dont care 1 women
        isdirty                         = int(isdirty)

        if house_type == 0 or house_type == 5:
            house_type = 0
            if house_size == 8:
                house_size = 12
            elif house_size == 9:
                house_size = 20
            elif house_size == 10:
                house_size = 30
            elif house_size == 11:
                house_size = 40
            elif house_size == 12:
                house_size = 54
        elif house_type == 1 or house_type == 6:
            house_type = 1
            if house_size == 13:
                house_size = 7
            elif house_size == 14:
                house_size = 13
            elif house_size == 15:
                house_size = 19
            elif house_size == 16:
                house_size = 29
            elif house_size == 18:
                house_size = 54
        elif house_type == 2 or house_type == 7:
            house_type = 1
            if house_size == 19:
                house_size = 24
            elif house_size == 20:
                house_size = 34
            elif house_size == 21:
                house_size = 44
            elif house_size == 22:
                house_size = 54

        # logging part
        mix = get_mixpanel()
        mongo_logger = get_mongo_logger()

        try:
            scheduler = HMScheduler()

            userdao = UserDAO()
            addrdao = AddressDAO()

            print 'request available_schedules 11'
            print address
            print house_size
            print house_type
            print appointment_type
            print additional_task
            print have_pet
            print master_gender
            print isdirty
            print '--------------------------------'

            if additional_task == 64:
                additional_task = 0

            basic_address   = address.rsplit(',', 1)[0]
            detail_address  = address.rsplit(',', 1)[1]

            print "basic_address : ", basic_address
            print "detail_address : ", detail_address

            # get gu_id & geohash
            full_address = '%s %s' % (basic_address, detail_address)
            print "full_address : ", full_address
            lat, lng    = get_latlng_from_address(full_address)
            geohash6   = get_geohash(lat, lng, 6)
            gu_id       = addrdao.get_gu_id(basic_address)

            if gu_id == '':
                raise Exception('gu id is incorrect')

            tp_key, time, price, first_time = get_time_price(appointment_type, house_type, house_size)
            cleaning_time = time + first_time

            task_time, task_price = get_additional_task_time_price(additional_task, house_type, house_size)

            comb_key = '%s_%d_%d_%d' % (tp_key, additional_task, have_pet, master_gender)

            # total time and price
            total_taking_time_in_minutes = cleaning_time + task_time

            available_schedules = scheduler.get_available_slots(gu_id = gu_id, geohash = geohash6, appointment_type = appointment_type, taking_time = total_taking_time_in_minutes,
                                                                prefer_women = True if master_gender == 1 else False,
                                                                have_pet = True if have_pet == 1 else False,
                                                                isdirty = True if isdirty == 1 else False)


            now = dt.datetime.now()
            if now.hour >= 17: # 7시 이후 라면 -> 5시로 변경
                tomorrow = now + dt.timedelta(days=1)
                tomorrow = dt.datetime.strftime(tomorrow, '%Y%m%d')
                if tomorrow in available_schedules:
                    del available_schedules[tomorrow]


            #for day in available_schedules:
            #    print '[', day, ']'
            #    print available_schedules[day]['by_time']

            print '11 street log'
            # log to mixpanel
            #mix.track(uid, '11 request available schedule', {'time' : dt.datetime.now(), 'taking_time' : taking_time, 'additional_time' : additional_time, 'appointment_type' : appointment_type, 'have_pet' : have_pet, 'master_gender' : master_gender,'isdirty' : isdirty})

            # log to mongo
            mongo_logger.debug('11 request available schedule', extra = {'taking_time' : cleaning_time, 'additional_time' : task_time, 'appointment_type' : appointment_type, 'have_pet' : have_pet, 'master_gender' : master_gender,'isdirty' : isdirty})

            if len(available_schedules) > 0: # 가능한 날짜가 있다면
                ret['response'] = available_schedules
                ret['comb_key'] = comb_key
                print comb_key
            else:
                add_err_message_to_response(ret, err_dict['err_not_available'])

            self.set_status(Response.RESULT_OK)
        except Exception, e:
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)
            mongo_logger.error('error 11 request available schedules', extra = {'err' : str(e)})

        finally:
            self.write(json.dumps(ret))
