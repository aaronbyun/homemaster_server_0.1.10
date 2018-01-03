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
import requests
import datetime as dt
from data.dao.userdao import UserDAO
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, User, UserAddress, UserDefaultAddress
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel
from sender.jandi_sender import send_jandi

from payment.payment_helper import request_payment_web
from pymongo import ReturnDocument

try:
    from utils.secrets import PAYMENT_HOST, PAYMENT_PORT, MONGO_USER, MONGO_PWD
except ImportError:
    PAYMENT_HOST = 'localhost'
    PAYMENT_PORT = 8443
    MONGO_USER  = ''
    MONGO_PWD = ''


class RegisterCardAndChargeHandler(tornado.web.RequestHandler):
    def initialize(self, mongo):

        self.mongo = mongo
        booking = mongo.booking
        booking.authenticate(MONGO_USER, MONGO_PWD, source = 'booking')

        self.db = booking.customer

    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        cleaning_id     = self.get_argument('cleaning_id', '')
        cno             = self.get_argument('cno', '')
        expy            = self.get_argument('expy', '')
        expm            = self.get_argument('expm', '')
        ssnf            = self.get_argument('ssnf', '')
        cpftd           = self.get_argument('cpftd', '')
        calias          = self.get_argument('calias', '')

        ret = {}

        try:
            mongo_logger = get_mongo_logger()
            mix = get_mixpanel()

            userdao = UserDAO()

            doc = self.db.find_one_and_update({'cleaning_id' : cleaning_id},
                                            {'$set' : {'payment' : '선결제'}},
                                            return_document = ReturnDocument.AFTER)
            if doc == None:
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_no_cleaning_id'])
                return

            print cno

            try:
                uid    = doc['user_id']
            except Exception, e:
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_no_user_id'])
                return

            try:
                amount = int(doc['total_price'])
            except Exception, e:
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_invalid_amount'])
                return

            address = doc['address']
            period  = doc['period']
            dates   = ','.join(doc['dates'])
            start_date = doc['start_date']

            request_url = '%s:%d/homemaster_payment/register_card' % (PAYMENT_HOST, PAYMENT_PORT)
            params = {}
            params['id'] = uid
            params['cno'] = cno
            params['expy'] = expy
            params['expm'] = expm
            params['ssnf'] = ssnf
            params['cpftd'] = cpftd
            params['calias'] = calias

            response = requests.post(request_url, data = params)
            result = json.loads(response.text)

            if response.status_code == 200 and result['response'] != "":
                mix.track(uid, 'register card', {'time' : dt.datetime.now(), 'calias' : calias})
                mongo_logger.debug('%s registered card' % uid, extra = {'user_id' : uid})

                user_name = userdao.get_user_name(uid)
                user_phone = userdao.get_user_phone(uid)


                import redis
                try:
                    from utils.secrets import REDIS_HOST, REDIS_PORT, REDIS_PWD
                except ImportError:
                    REDIS_HOST = 'localhost'
                    REDIS_PORT = 6379
                    REDIS_PWD = ''

                r = redis.Redis(host = REDIS_HOST, port = REDIS_PORT, password = REDIS_PWD)
                event_on = r.get('free_event')

                if period in ['매주여러번', '매주한번'] and event_on:
                    result = True
                    msg = ''
                else:
                    result, msg = request_payment_web(uid, user_name, amount)

                if result:
                    ret['response'] = Response.SUCCESS

                    # jandi notification
                    description = '{}({}) 고객님, 예약됨 {} {} - {}, {}'.format(user_name,
                                                    user_phone, period, address, start_date,
                                                    dates)

                    send_jandi('NEW_WEB', '[웹]신규예약', '선결제', description)
                else:
                    ret['response'] = ''
                    ret['err_msg'] = msg

                self.set_status(Response.RESULT_OK)

                mongo_logger.debug('request payment web', extra = {'user_id' : uid,
                                                                   'amount' : amount})
            else:
                print 'An error occurred while register card'
                print result['err_code'], result['err_msg']
                add_err_ko_message_to_response(ret, result['err_msg'])

                mix.track(uid, 'cannot register card', {'time' : dt.datetime.now()})
                mongo_logger.error('%s failed to register card' % uid, extra = {'err' : result['err_msg']})
        except Exception, e:
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            self.write(json.dumps(ret))
