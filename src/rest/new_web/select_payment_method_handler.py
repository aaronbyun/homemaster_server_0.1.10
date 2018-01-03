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
import datetime as dt
from data.session.mysql_session import engine, Session
from data.model.data_model import User
from err.error_handler import print_err_detail, err_dict
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from data.encryption import aes_helper as aes
from data.dao.addressdao import AddressDAO
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel
from sender.jandi_sender import send_jandi
from sender.alimtalk_sender import send_alimtalk
from pymongo import ReturnDocument

try:
    from utils.secrets import MONGO_USER, MONGO_PWD
except ImportError:
    MONGO_HOST = ''
    DB_PORT = ''

class SelectPaymentMethodHandler(tornado.web.RequestHandler):
    def initialize(self, mongo):

        self.mongo = mongo
        booking = mongo.booking
        booking.authenticate(MONGO_USER, MONGO_PWD, source = 'booking')

        self.db = booking.customer

    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        cleaning_id = self.get_argument('cleaning_id', '')
        payment = self.get_argument('payment', '')

        ret = {}

        mongo_logger = get_mongo_logger()

        try:
            addressdao = AddressDAO()
            doc = self.db.find_one_and_update({'cleaning_id' : cleaning_id},
                                            {'$set' : {'payment' : '후결제'}},
                                            return_document = ReturnDocument.AFTER)

            if payment == '현장결제':
                # jandi notification
                description = '{}({}) 고객님, 예약됨 {} {} - {}, {}'.format(doc['name'],
                            doc['phone'], doc['period'], doc['address'], doc['start_date'],
                            ','.join(doc['dates']))
                send_jandi('NEW_WEB', '[웹]신규예약', '후결제', description)

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

            mongo_logger.debug('web select payment',
                                            extra = {'cleaning_id' : cleaning_id,
                                                    'payment' : payment})

        except Exception, e:
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)
            mongo_logger.error('failed to web select payment',
                                                  extra = {'cleaning_id' : cleaning_id,
                                                            'payment' : payment})

        finally:
            self.write(json.dumps(ret))
