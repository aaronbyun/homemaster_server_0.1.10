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

from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.session.mysql_session import engine, Session
from data.model.data_model import UserAddress, UserDefaultAddress
from data.dao.userdao import UserDAO
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class UserAddressInfoHandler(tornado.web.RequestHandler):
    def get(self):
        ret = {}

        user_id         = self.get_argument('user_id', '')
        address_index   = self.get_argument('address_index', '')

        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        try:
            userdao = UserDAO()
            address, size, kind, rooms, baths = userdao.get_user_address_full_detail_by_index(user_id, address_index)

            address_info = {}
            address_info['rooms'] = rooms
            address_info['size'] = size
            address_info['kind'] = kind
            address_info['baths'] = baths
            address_info['address'] = address

            ret['response'] = address_info
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)

        finally:
            self.write(json.dumps(ret))
