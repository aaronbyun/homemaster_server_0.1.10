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
import booking.booking_constant as BC
from sqlalchemy import func, or_, and_
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, User, UserPaymentRecordForIOS, UserFreeEvent
from data.dao.userdao import UserDAO
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response2
from err.error_handler import print_err_detail, err_dict
from payment.payment_helper import request_payment
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from data.encryption import aes_helper as aes

class BookingChargeHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        booking_id      = self.get_argument('booking_id', '')
        price           = self.get_argument('price', '')

        # price int
        price = int(price)

        ret = {}

        try:
            session = Session()

            try:
                row = session.query(Booking, User) \
                        .join(User, Booking.user_id == User.id) \
                        .filter(Booking.id == booking_id) \
                        .one()

            except NoResultFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_login_no_record'])
                return

            except MultipleResultsFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_multiple_record'])
                return

            userdao = UserDAO()
            user_id = row.User.id
            appointment_type = row.Booking.appointment_type

            # 1회 무료 이벤트 해당 고객이라면
            import redis
            try:
                from utils.secrets import REDIS_HOST, REDIS_PORT, REDIS_PWD
            except ImportError:
                REDIS_HOST = 'localhost'
                REDIS_PORT = 6379
                REDIS_PWD = ''

            r = redis.Redis(host = REDIS_HOST, port = REDIS_PORT, password = REDIS_PWD)
            event_on = r.get('free_event')

            key = userdao.get_user_salt_by_id(user_id)[:16]
            crypto = aes.MyCrypto(key)

            user_name = crypto.decodeAES(row.User.name)
            appointment_type = row.Booking.appointment_type


            charging_price = price
            if appointment_type == 4 and event_on:
                charging_price = row.Booking.price_with_task

            if charging_price <= 0:
                ret_code = True
                value    = ''
            else:
                ret_code, value = request_payment(user_id, user_name, booking_id, charging_price, appointment_type, 'PAID')

            if ret_code == True:
                print booking_id
                row.Booking.status          = BC.BOOKING_PAID
                row.Booking.payment_status  = BC.BOOKING_PAID
                row.Booking.tid             = value

                session.commit()

                ret['response'] = Response.SUCCESS
            else:
                add_err_ko_message_to_response2(ret, '5011', value)

            self.set_status(Response.RESULT_OK)

        except Exception, e:
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))
