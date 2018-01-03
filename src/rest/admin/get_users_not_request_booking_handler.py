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
from data.session.mysql_session import engine, Session
from data.model.data_model import User, UserAddress, UserDefaultAddress, Booking
from data.dao.userdao import UserDAO
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.encryption import aes_helper as aes
from sqlalchemy import and_

class UserNotRequestBookingHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        try:
            session = Session()
            userdao = UserDAO()            

            users = []

            for row in session.query(User, UserAddress, UserDefaultAddress, Booking) \
                            .outerjoin(UserAddress, User.id == UserAddress.user_id) \
                            .outerjoin(UserDefaultAddress, User.id == UserDefaultAddress.user_id) \
                            .outerjoin(Booking, and_(User.id == Booking.user_id)) \
                            .all():

                if row.UserAddress != None and row.Booking == None:
                    user_id = row.User.id
                    key = userdao.get_user_salt_by_id(user_id)[:16]
                    crypto = aes.MyCrypto(key)

                    user_info = {}
                    user_info['name']               = crypto.decodeAES(row.User.name)
                    user_info['phone']              = crypto.decodeAES(row.User.phone)

                    users.append(user_info)

            ret['response'] = users
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
            
        finally:
            session.close()
            self.write(json.dumps(ret))