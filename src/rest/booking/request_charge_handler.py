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


class RequestChargeHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")

        uid     = self.get_argument('uid', '')
        price   = self.get_argument('price', '')

        ret = {}

        try:
            mongo_logger = get_mongo_logger()
            mix = get_mixpanel()

            userdao = UserDAO()

            request_url = '%s:%d/homemaster_payment/request_payment' % (PAYMENT_HOST, PAYMENT_PORT)

            params = {}
            params['id']            = uid
            params['name']          = userdao.get_user_name(uid)
            params['price']         = price
            params['product_name']  = 'moving'
            

            response = requests.post(request_url, data = params)
            result = json.loads(response.text)

            if response.status_code == 200 and result['response'] == "SUCCESS":
                mix.track(uid, 'request mc payment', {'time' : dt.datetime.now(), 'tid' : result['tid'], 'authdate' : result['authdate']})
                mongo_logger.debug('%s request mc payment' % uid, extra = {'user_id' : uid, 'tid' : result['tid'], 'authdate' : result['authdate']})
                
                ret['response'] = result['response']
                self.set_status(Response.RESULT_OK)
            else:
                print 'An error occurred when paying moving clean'
                print result['err_code'], result['err_msg']
                add_err_ko_message_to_response(ret, result['err_msg'])

                mix.track(uid, 'cannot request mc payment', {'time' : dt.datetime.now(), 'code' : result['err_code']})
                mongo_logger.error('%s failed to request mc payment' % uid, extra = {'err' : result['err_msg']})
        except Exception, e:
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            self.write(json.dumps(ret))