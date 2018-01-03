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
from data.model.data_model import Booking, User, UserPaymentRecordForIOS
from data.dao.userdao import UserDAO
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from err.error_handler import print_err_detail, err_dict
from payment.payment_helper import request_payment
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from data.encryption import aes_helper as aes

class ManualChargeHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        booking_id = self.get_argument('booking_id', '')
        price = self.get_argument('price', '')
        product_name = self.get_argument('product_name', '')

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

            key = userdao.get_user_salt_by_id(user_id)[:16]
            crypto = aes.MyCrypto(key)

            user_name = crypto.decodeAES(row.User.name)
            appointment_type = row.Booking.appointment_type

            if row.User.devicetype == 'None':
                try:
                    record = UserPaymentRecordForIOS(booking_id, user_id, price, dt.datetime.now())
                    session.add(record)
                    session.commit()
                    ret_code = True
                except Exception, e:
                    ret_code  = False
                    value = str(e)
            else:
                ret_code, value = request_payment(user_id, user_name, booking_id, price, appointment_type, 'CHARGED')

            if ret_code == True:
                ret['response'] = Response.SUCCESS
            else:
                add_err_ko_message_to_response(ret, value)

            self.set_status(Response.RESULT_OK)

        except Exception, e:
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))
