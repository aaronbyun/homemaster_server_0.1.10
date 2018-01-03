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
try:
    from utils.secrets import PAYMENT_HOST, PAYMENT_PORT
except ImportError:
    PAYMENT_HOST = 'localhost'
    PAYMENT_PORT = 8443


class CancelPaymentHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        user_id         = self.get_argument('id', '')
        tid             = self.get_argument('tid', '')
        amount          = self.get_argument('amount', 0)
        partial         = self.get_argument('partial', 1)
        cancel_msg      = self.get_argument('cancel_msg', '')

        amount = int(amount)

        if cancel_msg == '':
            cancel_msg = '취소'

        ret = {}

        try:
            mongo_logger = get_mongo_logger()
            mix = get_mixpanel()

            userdao = UserDAO()

            request_url = '%s:%d/homemaster_payment/cancel_payment' % (PAYMENT_HOST, PAYMENT_PORT)
            params = {}
            params['id'] = user_id
            params['tid'] = tid
            params['amount'] = amount
            params['partial'] = partial
            params['cancel_msg'] = cancel_msg

            response = requests.post(request_url, data = params)
            result = json.loads(response.text)

            if response.status_code == 200 and result['response'] != "":
                mix.track(user_id, 'cancel payment', {'time' : dt.datetime.now()})
                mongo_logger.debug('cancel payment', extra = {'user_id' : user_id})

                ret['response'] = result['response']
                self.set_status(Response.RESULT_OK)
            else:
                print 'An error occurred while register card'
                print result['err_msg']
                add_err_ko_message_to_response(ret, result['err_msg'])
                mix.track(user_id, 'cannot cancel payment', {'time' : dt.datetime.now()})
                mongo_logger.error('failed to cancel payment', extra = {'user_id' : user_id})
        except Exception, e:
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            self.write(json.dumps(ret))
