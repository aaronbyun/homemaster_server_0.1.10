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
from sqlalchemy import and_, or_, func, not_
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, User, Master, UserClaim
from data.dao.userdao import UserDAO
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.encryption import aes_helper as aes
from sqlalchemy import desc

class UnpaidListHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        ret = {}

        try:
            session = Session()

            result = session.query(Booking, User) \
                            .join(User, and_(Booking.user_id == User.id, and_(or_(Booking.cleaning_status == 1, Booking.cleaning_status == 2), or_(Booking.payment_status == 0, Booking.payment_status == -3)))) \
                            .filter(not_(User.email.like('%@b2b.com'))) \
                            .all()
            unpaid_datas = []
            Userdao = UserDAO()

            for record in result:
                key = Userdao.get_user_salt(record.User.email)[:16]
                if key == None or key == '':
                    continue

                crypto = aes.MyCrypto(key)

                unpaid_info = {}
                unpaid_info['booking_id']       = record.Booking.id
                unpaid_info['appointment_type'] = record.Booking.appointment_type
                unpaid_info['cleanning_date']   = dt.datetime.strftime(record.Booking.start_time, '%Y-%m-%d %H:%M')
                unpaid_info['user_name']        = crypto.decodeAES(record.User.name)
                unpaid_info['user_phone']       = crypto.decodeAES(record.User.phone)
                unpaid_info['price_with_task']  = record.Booking.price_with_task
                unpaid_datas.append(unpaid_info)

            ret['response'] = unpaid_datas;
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))
