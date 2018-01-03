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
from data.model.data_model import User, UserAddress, UserDefaultAddress
from data.dao.userdao import UserDAO
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.encryption import aes_helper as aes
from sqlalchemy import desc

class AllUserInfoHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        try:
            session = Session()

            users = []

            userdao = UserDAO()

            for row in session.query(User, UserAddress) \
                            .outerjoin(UserDefaultAddress, UserDefaultAddress.user_id == User.id) \
                            .outerjoin(UserAddress, and_(UserDefaultAddress.user_id == UserAddress.user_id, UserDefaultAddress.address_idx == UserAddress.user_addr_index)) \
                            .order_by(desc(User.dateofreg)) \
                            .all():

                key = userdao.get_user_salt(row.User.email)[:16]
                crypto = aes.MyCrypto(key)

                user_info = {}
                user_info['user_id']    = row.User.id
                user_info['dateofreg']  = dt.datetime.strftime(row.User.dateofreg, '%Y-%m-%d %H:%M')
                user_info['devicetype'] = row.User.devicetype
                user_info['name']       = crypto.decodeAES(row.User.name)
                user_info['email']      = row.User.email
                user_info['phone']      = crypto.decodeAES(row.User.phone)
                user_info['gender']     = row.User.gender
                user_info['birthdate']  = crypto.decodeAES(row.User.dateofbirth)
                user_info['default_address'] = crypto.decodeAES(row.UserAddress.address) if row.UserAddress != None else ''
                user_info['default_address_size'] = row.UserAddress.size if row.UserAddress != None else ''
                user_info['default_address_kind'] = row.UserAddress.kind if row.UserAddress != None else ''

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