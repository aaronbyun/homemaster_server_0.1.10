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
from data.model.data_model import User, Booking
from data.encryption import aes_helper as aes
from data.dao.userdao import UserDAO
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict

class IOSNoneCustomerHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        try:
            session = Session()
            userdao = UserDAO()

            none_ios_users = []

            for row in session.query(User, Booking) \
                            .join(Booking, User.id == Booking.user_id) \
                            .filter(Booking.cleaning_status == 0) \
                            .filter(User.devicetype == 'None') \
                            .group_by(User.id) \
                            .all():
                user_dict = {}

                user_id = row.User.id
                key = userdao.get_user_salt_by_id(user_id)[:16]
                crypto = aes.MyCrypto(key)

                user_dict['name']               = crypto.decodeAES(row.User.name)
                user_dict['email']              = row.User.email
                user_dict['phone']              = crypto.decodeAES(row.User.phone)
                user_dict['gender']             = row.User.gender

                none_ios_users.append(user_dict)

            print len(none_ios_users)
            ret['response'] = none_ios_users
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))