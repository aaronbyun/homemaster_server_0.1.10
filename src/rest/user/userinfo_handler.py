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

class UserInfoHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        user_id = self.get_argument('user_id', '')

        ret = {}

        if user_id == '':
            self.set_status(Response.RESULT_BADREQUEST)
            add_err_message_to_response(ret, err_dict['invalid_param'])
            self.write(json.dumps(ret))
            return

        mongo_logger = get_mongo_logger()
        mix = get_mixpanel()

        try:
            session = Session()

            userdao = UserDAO()

            key = userdao.get_user_salt_by_id(user_id)[:16]
            crypto = aes.MyCrypto(key)

            user_info = {}
            addresses = []

            for row in session.query(User, UserAddress, UserDefaultAddress) \
                            .outerjoin(UserAddress, User.id == UserAddress.user_id) \
                            .outerjoin(UserDefaultAddress, User.id == UserDefaultAddress.user_id).filter(User.id == user_id) \
                            .order_by(UserAddress.user_addr_index) \
                            .all():
                if row.UserAddress != None:
                    kind = row.UserAddress.kind
                    if kind == 3:
                        kind = 0

                    addr = {'addr' : crypto.decodeAES(row.UserAddress.address), 'size' : row.UserAddress.size, 'kind' : kind, 'index' : row.UserAddress.user_addr_index}
                    addresses.append(addr)

                default_idx = -1
                if row.UserDefaultAddress != None:
                    default_idx = row.UserDefaultAddress.address_idx

                user_info['name']               = crypto.decodeAES(row.User.name)
                user_info['email']              = row.User.email
                user_info['phone']              = crypto.decodeAES(row.User.phone)
                user_info['gender']             = row.User.gender
                user_info['auth_source']        = row.User.authsource
                user_info['devicetype']         = row.User.devicetype
                user_info['birthdate']          = crypto.decodeAES(row.User.dateofbirth)
                user_info['default_addr_idx']   = default_idx

            user_info['arr_address'] = addresses

            ret['response'] = user_info
            self.set_status(Response.RESULT_OK)

            mix.track(user_id, 'got userinfo', {'time' : dt.datetime.now()})
            mongo_logger.debug('got userinfo', extra = {'user_id' : user_id})

            print 'userinfo was successfully retrieved to', user_info['name']

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

            mix.track(user_id, 'failed to got userinfo', {'time' : dt.datetime.now()})
            mongo_logger.debug('failed to got userinfo', extra = {'user_id' : user_id})

        finally:
            session.close()
            self.write(json.dumps(ret))
