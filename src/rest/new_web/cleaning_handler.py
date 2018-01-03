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

class CleaningHandler(tornado.web.RequestHandler):
    def initialize(self, mongo):
        self.mongo = mongo
        booking = mongo.booking
        booking.authenticate(MONGO_USER, MONGO_PWD, source = 'booking')

        self.db = booking.customer

    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        mongo_logger = get_mongo_logger()

        ret = {}
        web_bookings = []

        try:
            docs = self.db.find({'$where' : 'this.dates.length > this.count',
                                'payment' : {'$exists' : True},
                                'removed' : {'$exists' : False}}) \
                        .sort('request_time', pymongo.DESCENDING)
            for doc in docs:
                booking = {}
                booking['name']         = doc['name']
                booking['phone']        = doc['phone']
                booking['address']      = doc['address']
                booking['address_index']      = doc['address_index']
                booking['dates']        = doc['dates']
                booking['start_date']        = doc['start_date'] if 'start_date' in doc else ''
                booking['time']         = doc['time']
                booking['user_id']      = doc['user_id']
                booking['cleaning_id']  = doc['cleaning_id']
                booking['tasks']        = doc['tasks']
                booking['rooms']        = doc['rooms']
                booking['baths']        = doc['baths']
                booking['size']        = doc['size'] if 'size' in doc else 0
                booking['total_price']        = doc['total_price']
                booking['total_duration']     = doc['total_duration']
                booking['basic_price']        = doc['basic_price']
                booking['basic_duration']     = doc['basic_duration']
                booking['period']       = doc['period']
                booking['email']        = doc['email']
                booking['dirty']        = doc['dirty']
                booking['payment']      = doc['payment']
                booking['count']        = doc['count']
                booking['message']      = doc['message']
                booking['request_time'] = dt.datetime.strftime(doc['request_time'], '%Y-%m-%d %H:%M')

                booking['contact_cnt']      = doc['contact_cnt'] if 'contact_cnt' in doc else '0회'
                booking['contact_memo']     = doc['contact_memo'] if 'contact_memo' in doc else ''

                web_bookings.append(booking)

            ret['response'] = web_bookings
            self.set_status(Response.RESULT_OK)

            mongo_logger.debug('web booking')

        except Exception, e:
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)
            mongo_logger.error('failed to web booking')

        finally:
            self.write(json.dumps(ret))
