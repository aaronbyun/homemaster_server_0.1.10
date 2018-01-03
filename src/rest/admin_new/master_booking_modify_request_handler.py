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
import requests
from bson.timestamp import Timestamp
from data.session.mysql_session import engine, Session
from data.model.data_model import MasterBookingModifyRequest, Booking, UserAddress
from data.dao.masterdao import MasterDAO
from data.dao.userdao import UserDAO
from data.dao.addressdao import AddressDAO
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.encryption import aes_helper as aes
from sqlalchemy import and_, func
from utils.datetime_utils import convert_datetime_format2
from sender.alimtalk_sender import send_alimtalk
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sender.jandi_sender import send_jandi
try:
    from utils.secrets import MANAGERS_CALL
except ImportError:
    MANAGERS_CALL = ''

class MasterBookingModifyRequestHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        booking_id = self.get_argument('booking_id', '')
        reason     = self.get_argument('reason', '')
        print booking_id, reason

        ret = {}

        try:
            session = Session()

            userdao = UserDAO()
            masterdao = MasterDAO()
            addressdao = AddressDAO()

            now = dt.datetime.now().date() + dt.timedelta(days=2)

            row = session.query(Booking) \
                        .filter(Booking.id == booking_id) \
                        .filter(Booking.cleaning_status == 0) \
                        .filter(func.date(Booking.start_time) >= now) \
                        .one()

            master_id = row.master_id
            start_time = row.start_time

            request = MasterBookingModifyRequest(master_id = master_id, booking_id = booking_id,
                                                reason = reason, org_time = start_time,
                                                request_time = dt.datetime.now())
            session.add(request)
            session.commit()

            row = session.query(Booking, UserAddress) \
                    .join(UserAddress, and_(Booking.user_id == UserAddress.user_id, Booking.addr_idx == UserAddress.user_addr_index)) \
                    .filter(Booking.id == booking_id) \
                    .one()

            master_name = masterdao.get_master_name(row.Booking.master_id)
            user_name = userdao.get_user_name(row.Booking.user_id)
            district = addressdao.get_gu_name(userdao.get_user_address(row.Booking.user_id)[0])
            appointment_time = convert_datetime_format2(row.Booking.start_time)

            for manager_phone in MANAGERS_CALL.split(','):
                send_alimtalk(manager_phone, 'noti_manager_modify_schedule', master_name, user_name, district, appointment_time)

            send_jandi('HOMEMASTER_REST', "휴무 신청", master_name + ' 홈마스터님 일정변경 신청', '고객 : {}\n지역 : {}\n일정 : {}'.format(user_name, district, appointment_time))

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

            print 'booking_id', booking_id, 'was requested to modify'

        except NoResultFound, e:
            session.close()
            self.set_status(Response.RESULT_OK)
            add_err_ko_message_to_response(ret, '해당일은 일정 변경이 불가능 합니다. 일정 변경은 최소 이틀전에 가능합니다.')
            return

        except MultipleResultsFound, e:
            session.close()
            self.set_status(Response.RESULT_OK)
            add_err_ko_message_to_response(ret, '일정 변경 중 에러가 발생했습니다.')
            return

        except Exception, e:
            session.rollback()
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()
            self.write(json.dumps(ret))
