#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')

import json
import tornado.ioloop
import tornado.web
import uuid
import hashlib
import base64
import pymongo
import datetime as dt
from data.session.mysql_session import engine, Session
from data.model.data_model import User
from err.error_handler import print_err_detail, err_dict
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from data.encryption import aes_helper as aes
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel


try:
    from utils.secrets import MONGO_USER, MONGO_PWD
except ImportError:
    MONGO_HOST = ''
    DB_PORT = ''

class ProcessCleaningHandler(tornado.web.RequestHandler):
    def initialize(self, mongo):
        self.mongo = mongo
        booking = mongo.booking
        booking.authenticate(MONGO_USER, MONGO_PWD, source = 'booking')

        self.db = booking.customer

    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        cleaning_id     = self.get_argument('cleaning_id', '')
        booking_id      = self.get_argument('booking_id', '')

        mongo_logger = get_mongo_logger()

        ret = {}
        try:
            doc = self.db.find_one_and_update({'cleaning_id' : cleaning_id},
                                            {'$push' : {'booking_ids' : booking_id},
                                            '$inc' : {'count' : 1}})

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

            mongo_logger.debug('web process booking')

        except Exception, e:
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)
            mongo_logger.error('failed to web process booking')

        finally:
            self.write(json.dumps(ret))
