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
from logger.mongo_logger import get_mongo_logger
from data.encryption import aes_helper as aes

try:
    from utils.secrets import MONGO_USER, MONGO_PWD
except ImportError:
    MONGO_HOST = ''
    DB_PORT = ''

class UserChecklistHandler(tornado.web.RequestHandler):
    def initialize(self, mongo):

        self.mongo = mongo
        checklist = mongo.checklist
        checklist.authenticate(MONGO_USER, MONGO_PWD, source = 'checklist')

        self.col = checklist.checklist

    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        booking_id = self.get_argument('booking_id', '')
        ret = {}

        try:
            checklist = self.col.find_one({'booking_id' : booking_id})
            ret['response'] = checklist if checklist != None else ''
            
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            self.write(json.dumps(ret))
