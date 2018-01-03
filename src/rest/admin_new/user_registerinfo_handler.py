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
from data.model.data_model import User, UserAddress, UserDefaultAddress
from data.dao.userdao import UserDAO
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.encryption import aes_helper as aes
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import and_, or_, func, desc

class UserRegisterInfoHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        phone = self.get_argument('phone', '')

        print 'phone', phone

        mongo_logger = get_mongo_logger()

        ret = {}

        try:
            session = Session()
            userdao = UserDAO()

            try:
                result = session.query(User) \
                            .filter(func.aes_decrypt(func.from_base64(User.phone), \
                            func.substr(User.salt, 1, 16)) == phone,  \
                            User.active == 1) \
                            .all()

            except NoResultFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_login_no_match'])
                mongo_logger.error('%s failed to get registerinfo' % phone, extra = {'err' : str(e)})
                return

            usersinfo = []

            for row in result:
                userinfo = {}
                userinfo['id']     = row.id
                userinfo['name']   = userdao.get_user_name(row.id)
                userinfo['phone']  = userdao.get_user_phone(row.id)
                userinfo['email']  = row.email
                usersinfo.append(userinfo)

            mongo_logger.debug('user registered info')

            ret['response'] = usersinfo
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
            mongo_logger.error('failed to get registerinfo')

        finally:
            session.close()
            self.write(json.dumps(ret))
