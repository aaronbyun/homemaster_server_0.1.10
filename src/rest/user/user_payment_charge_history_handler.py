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
from sqlalchemy import and_
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, UserPaymentRecord, UserChargeRecord, User, UserAddress, Master, Promotion, EventPromotionBooking
from data.dao.userdao import UserDAO
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.encryption import aes_helper as aes
from sqlalchemy import desc
from utils.datetime_utils import convert_datetime_format2, convert_datetime_format3

class UserPaymentChargeHistoryHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        user_id = self.get_argument('user_id', '')

        ret = {}

        try:
            session = Session()
            userdao = UserDAO()

            payment_histories = []

            result = session.query(UserChargeRecord, User) \
                            .join(User, UserChargeRecord.user_id == User.id) \
                            .filter(UserChargeRecord.user_id == user_id) \
                            .order_by(desc(UserChargeRecord.auth_date)) \
                            .all()

            for row in result:
                try:
                    auth_date       = '20' + row.UserChargeRecord.auth_date
                    auth_date = dt.datetime.strptime(auth_date, '%Y%m%d%H%M%S')
                except Exception, e:
                    auth_date = None

                payment_info = {}
                payment_info['tid']                 = row.UserChargeRecord.tid
                payment_info['amount']              = row.UserChargeRecord.amount
                payment_info['auth_date']           = convert_datetime_format2(auth_date) if auth_date != None else ''

                payment_histories.append(payment_info)

            user_name = userdao.get_user_name(user_id)
            user_phone = userdao.get_user_phone(user_id)

            ret['response'] = {'user_id' : user_id, 'name' : user_name, 'phone' : user_phone, 'payment_histories' : payment_histories }
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))
