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
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.encryption import aes_helper as aes

try:
    from utils.stipulation_text import FAQ
except ImportError:
    FAQ = ''

class FAQHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        try:
            ret['response'] = FAQ
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            self.write(json.dumps(ret))
