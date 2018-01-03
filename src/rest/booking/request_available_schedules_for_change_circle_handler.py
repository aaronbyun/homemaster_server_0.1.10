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
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.exc import IntegrityError
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel


class RequestAvailableSchedulesForChangeCircleHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        ret = {}

        booking_id                  = self.get_argument('booking_id', '')
        appointment_type            = self.get_argument('appointment_type', 0)
        is_admin                    = self.get_argument('is_admin', 1)

        appointment_type            = int(appointment_type)
        is_admin                    = int(is_admin)


        print 'appointment_type', appointment_type

        # logging part
        mix = get_mixpanel()
        mongo_logger = get_mongo_logger()

        try:
            session = Session()
            try:
                row = session.query(Booking).filter(Booking.id == booking_id).one()
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

            uid                 = row.user_id
            have_pet            = row.havepet
            master_gender       = row.master_gender
            isdirty             = row.is_dirty
            start_time          = row.start_time
            estimated_end_time  = row.estimated_end_time
            appointment_date    = row.org_start_time
            request_id          = row.request_id
            addr_idx            = row.addr_idx

            print "orginal apointment type : " + str(row.appointment_type)

            total_taking_time_in_minutes = time_to_minutes(timedelta_to_time(estimated_end_time - start_time))

            scheduler = HMScheduler()

            userdao = UserDAO()
            addrdao = AddressDAO()
            address, geohash5, geohash6 = userdao.get_user_address_by_index(uid, addr_idx) # 편집의 경우에는, 예약된 주소를 이용한다.
            gu_id = addrdao.get_gu_id(address)

            if gu_id == '':
                raise Exception('gu id is incorrect')

            update = True
            available_schedules = scheduler.get_available_slots(gu_id = gu_id, geohash = geohash6, appointment_type = appointment_type, taking_time = total_taking_time_in_minutes,
                                                                prefer_women = True if master_gender == 1 else False,
                                                                have_pet = True if have_pet == 1 else False,
                                                                isdirty = True if isdirty == 1 else False,
                                                                user_id = uid)

            if is_admin == 0: # is_admin == False
                now = dt.datetime.now()
                if now.hour >= 17: # 7시 이후 라면 -> 5시로 변경
                    tomorrow = now + dt.timedelta(days=1)
                    tomorrow = dt.datetime.strftime(tomorrow, '%Y%m%d')
                    if tomorrow in available_schedules:
                        del available_schedules[tomorrow]

            for day in available_schedules:
                print '[', day, ']'
                print available_schedules[day]['by_time']
            print 'schdules for update...'

            print 'have_pet', have_pet
            print 'master_gender', master_gender
            print 'isdirty', isdirty
            print 'taking_time', total_taking_time_in_minutes
            print 'appointment_date', appointment_date
            print 'gu_id', gu_id

            # log to mixpanel
            mix.track(uid, 'request change circle schedule', {'time' : dt.datetime.now(), 'appointment_type' : appointment_type, 'have_pet' : have_pet, 'master_gender' : master_gender,'isdirty' : isdirty})

            # log to mongo
            mongo_logger.debug('request change circle schedule', extra = { 'user_id' : uid, 'appointment_type' : appointment_type, 'have_pet' : have_pet, 'master_gender' : master_gender,'isdirty' : isdirty})

            if len(available_schedules) > 0: # 가능한 날짜가 있다면
                ret['response'] = {'schedule' : available_schedules, 'first_date' : available_schedules.keys()[0]}
            else:
                add_err_message_to_response(ret, err_dict['err_not_available'])

            self.set_status(Response.RESULT_OK)
        except Exception, e:
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)
            mongo_logger.error('error request change circle schedules', extra = {'user_id' : uid, 'err' : str(e)})

        finally:
            self.write(json.dumps(ret))
