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

class SubmitChecklistHandler(tornado.web.RequestHandler):
    def initialize(self, mongo):

        self.mongo = mongo
        checklist = mongo.checklist
        checklist.authenticate(MONGO_USER, MONGO_PWD, source = 'checklist')

        self.col = checklist.checklist

    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        checklist = json.loads(self.request.body)

        try:
            ret = {}

            mongo_logger = get_mongo_logger()

            if not 'booking_id' in checklist:
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_no_booking_id_checklist'])
                return

            booking_id = checklist['booking_id']

            if self.col.find_one({'booking_id' : booking_id}):
                mongo_logger.debug('checklist already exists', extra = {'booking_id' : booking_id, 'dt' : dt.datetime.now()})
            else:
                self.col.insert_one(checklist)
                mongo_logger.debug('checklist submission', extra = {'booking_id' : booking_id, 'dt' : dt.datetime.now()})

            ret['response'] = Response.SUCCESS

            self.set_status(Response.RESULT_OK)

        except Exception, e:
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            self.write(json.dumps(ret))
