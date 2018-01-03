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
from data.model.data_model import Booking, User
from data.dao.userdao import UserDAO
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from err.error_handler import print_err_detail, err_dict
from payment.payment_helper import request_payment, request_unpaid_charge
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from data.encryption import aes_helper as aes

class ManualUnpaidChargeHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")

        user_id      = self.get_argument('user_id', '')
        amount       = self.get_argument('amount', '')
        interest     = self.get_argument('interest', '0')
        quota        = self.get_argument('quota', '00')

        amount = int(amount)

        ret = {}

        try:
            session = Session()

            try:
                row = session.query(User) \
                        .filter(User.id == user_id) \
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
            user_id = row.id

            key = userdao.get_user_salt_by_id(user_id)[:16]
            crypto = aes.MyCrypto(key)

            user_name = crypto.decodeAES(row.name)

            ret_code, value = request_unpaid_charge(user_id, user_name, amount, interest, quota)
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