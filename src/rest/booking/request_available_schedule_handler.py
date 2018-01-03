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
from sqlalchemy import func
from schedule.schedule_helper import HMScheduler
from nptime import nptime
from utils.datetime_utils import time_to_str, timedelta_to_time, time_to_minutes
from utils.geo_utils import get_moving_time
from data.session.mysql_session import engine, Session
from data.intermediate.value_holder import IntermediateValueHolder
from data.model.data_model import UserPaymentRecord, Booking, UserDefaultAddress, UserDefaultCard, BlockUser, User
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
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from data.encryption import aes_helper as aes
from sender.jandi_sender import send_jandi


class RequestAvailableSchedulesHandler(tornado.web.RequestHandler):
    def is_user_block(self, ret, uid):
        try:
            mongo_logger = get_mongo_logger()
            userdao = UserDAO()

            session = Session()
            result = session.query(User) \
                            .filter(User.id == uid) \
                            .one()

            key = userdao.get_user_salt_by_id(result.id)[:16]
            crypto = aes.MyCrypto(key)
            phone   = crypto.decodeAES(result.phone)

            row = session.query(BlockUser, User) \
                         .join(User, User.id == BlockUser.user_id) \
                         .filter(func.aes_decrypt(func.from_base64(User.phone), func.substring(User.salt, 1, 16)) == phone) \
                         .all()

            print row

            session.close()
            if len(row) > 0:
                self.set_status(Response.RESULT_OK)
                add_err_ko_message_to_response(ret, '현재 주문량이 많아 신규 예약이 불가능 합니다. 확실한 서비스 품질을 보증을 위해 바로 서비스를 제공해 드릴 수 없는 점 양해 부탁드립니다.')
                mongo_logger.debug('block user', extra = { 'user_id' : uid })
                ret['err_code'] = '4037' # 임시 처리
                return True

            return False

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
            return True

        except MultipleResultsFound, e:
            print_err_detail(e)
            session.close()
            self.set_status(Response.RESULT_OK)
            mongo_logger.debug('block user', extra = { 'user_id' : uid })
            add_err_message_to_response(ret, err_dict['err_multiple_record'])
            return True

    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        ret = {}

        uid                         = self.get_argument('uid', '')
        appointment_type            = self.get_argument('appointment_type', BC.ONE_TIME)
        taking_time                 = self.get_argument('taking_time', 25)
        first_added_time            = self.get_argument('first_added_time', 0)
        additional_time             = self.get_argument('additional_time', 0)
        have_pet                    = self.get_argument('have_pet', 0)
        master_gender               = self.get_argument('master_gender', 0)
        isdirty                     = self.get_argument('isdirty', 0)
        for_manager                 = self.get_argument('for_manager', '')

        # for b2b appointment
        user_address_idx            = self.get_argument('user_address_idx', -1)
        b2b                         = self.get_argument('b2b', '')

        # convert parameters
        appointment_type                = int(appointment_type)
        taking_time                     = int(taking_time)
        first_added_time                = int(first_added_time)
        additional_time                 = int(additional_time)

        taking_time_in_minutes          = taking_time * 6
        first_added_time_in_minutes     = first_added_time * 6
        additional_time_in_minutes      = additional_time * 6
        total_taking_time_in_minutes    = taking_time_in_minutes + first_added_time_in_minutes + additional_time_in_minutes

        have_pet                        = int(have_pet)
        master_gender                   = int(master_gender) # 0 dont care 1 women
        isdirty                         = int(isdirty)


        # logging part
        mix = get_mixpanel()
        mongo_logger = get_mongo_logger()

        try:
            if self.is_user_block(ret, uid) == True:
                return

            if appointment_type == BC.ONE_TIME_A_MONTH and b2b != 'b2b':
                self.set_status(Response.RESULT_OK)
                add_err_ko_message_to_response(ret, '4주 1회 서비스는 신규 예약을 지원하지 않습니다.')
                mongo_logger.debug('not booking one time a month', extra = { 'user_id' : uid })
                ret['err_code'] = '4038' # 임시 처리
                return


            if total_taking_time_in_minutes >= 600:
                self.set_status(Response.RESULT_OK)
                add_err_ko_message_to_response(ret, '클리닝 가능 시간을 초과하였습니다. (최대 10시간) 이전 화면으로 돌아가 추가사항을 2개이하로 줄여주세요.')
                ret['err_code'] = '4036' # 임시 처리
                return

            scheduler = HMScheduler()

            userdao = UserDAO()
            addrdao = AddressDAO()


            if user_address_idx == -1: # default_address
                address, geohash5, geohash6 = userdao.get_user_address(uid)
                _, size, kind = userdao.get_user_address_detail(uid)
            else: # address selection
                address, geohash5, geohash6 = userdao.get_user_address_by_index(uid, user_address_idx)
                _, size, kind = userdao.get_user_address_detail_by_index(uid, user_address_idx)

            gu_id = addrdao.get_gu_id(address)

            if gu_id == '':
                raise Exception('gu id is incorrect')

            available_schedules = scheduler.get_available_slots(gu_id = gu_id, geohash = geohash6, appointment_type = appointment_type, taking_time = total_taking_time_in_minutes,
                                                                prefer_women = True if master_gender == 1 else False,
                                                                have_pet = True if have_pet == 1 else False,
                                                                isdirty = True if isdirty == 1 else False,
                                                                user_id = uid)


            now = dt.datetime.now()
            if now.hour >= 17: # 7시 이후 라면 -> 5시로 변경 2016.06.03
                if for_manager == '': # 사용자 앱에서는 내일 예약 불가능
                    tomorrow = now + dt.timedelta(days=1)
                    tomorrow = dt.datetime.strftime(tomorrow, '%Y%m%d')
                    if tomorrow in available_schedules:
                        del available_schedules[tomorrow]

            for day in available_schedules:
                print '[', day, ']'
                print available_schedules[day]['by_time']
            # log to mixpanel
            mix.track(uid, 'request available schedule', {'time' : dt.datetime.now(), 'taking_time' : taking_time, 'additional_time' : additional_time, 'appointment_type' : appointment_type, 'have_pet' : have_pet, 'master_gender' : master_gender,'isdirty' : isdirty})

            # log to mongo
            mongo_logger.debug('request available schedule', extra = {'log_time' : dt.datetime.now(),  'user_id' : uid, 'taking_time' : taking_time, 'additional_time' : additional_time, 'appointment_type' : appointment_type, 'have_pet' : have_pet, 'master_gender' : master_gender,'isdirty' : isdirty})

            if len(available_schedules) > 0: # 가능한 날짜가 있다면
                ret['response'] = {'schedule' : available_schedules, 'first_date' : available_schedules.keys()[0] }
            else:
                add_err_message_to_response(ret, err_dict['err_not_available'])

                mongo_logger.debug('no masters', extra = {'log_time' : dt.datetime.now(), 'user_id' : uid, 'taking_time' : total_taking_time_in_minutes, 'gu_id' : gu_id, 'address' : address})
                user_name = userdao.get_user_name(uid)
                user_phone = userdao.get_user_phone(uid)
                send_jandi('BOOKING_NOT_AVAILABE', '예약 불가능 알림', '고객 : {} 전번 : {}'.format(user_name, user_phone),
                            '주기 : {}, 주소 : {}'.format(appointment_type, address))

            self.set_status(Response.RESULT_OK)
        except Exception, e:
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)
            mongo_logger.error('error request available schedules', extra = {'user_id' : uid, 'err' : str(e)})

        finally:
            self.write(json.dumps(ret))
