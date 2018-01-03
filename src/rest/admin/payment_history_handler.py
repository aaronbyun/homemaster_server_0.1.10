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
from sqlalchemy import func
from data.session.mysql_session import engine, Session
from data.model.data_model import UserPaymentRecord, User
from data.dao.userdao import UserDAO
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.encryption import aes_helper as aes
from sqlalchemy import desc

class PaymentHistoryHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")

        manager_id = self.get_argument('manager_id', '')

        ret = {}

        try:
            session = Session()
            userdao = UserDAO()

            payment_records = []

            result = session.query(UserPaymentRecord, User) \
                            .join(User, UserPaymentRecord.user_id == User.id) \
                            .order_by(UserPaymentRecord.user_id, desc(UserPaymentRecord.auth_date)) \
                            .all()

            for row in result:
                payment = {}

                key = userdao.get_user_salt_by_id(row.User.id)[:16]
                crypto = aes.MyCrypto(key)

                payment['tid']              = row.UserPaymentRecord.tid
                payment['booking_id']       = row.UserPaymentRecord.booking_id
                payment['user_id']          = row.UserPaymentRecord.user_id
                payment['price']            = row.UserPaymentRecord.price
                payment['auth_date']        = row.UserPaymentRecord.auth_date
                payment['canceled_amount']  = row.UserPaymentRecord.canceled_amount
                payment['canceled_date']    = row.UserPaymentRecord.canceled_date
                payment['status']           = row.UserPaymentRecord.status
                payment['user_name']        = crypto.decodeAES(row.User.name)
                payment['user_phone']       = crypto.decodeAES(row.User.phone)

                payment_records.append(payment)

            ret['response'] = payment_records
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))