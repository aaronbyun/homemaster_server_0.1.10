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


class UserCardHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        uid             = self.get_argument('user_id', '')

        ret = {}

        print uid
        print PAYMENT_HOST, PAYMENT_PORT

        try:
            mongo_logger = get_mongo_logger()
            mix = get_mixpanel()

            userdao = UserDAO()

            request_url = '%s:%d/homemaster_payment/get_cards' % (PAYMENT_HOST, PAYMENT_PORT)
            params = {}
            params['id'] = uid

            response = requests.get(request_url, params = params)
            print response
            result = json.loads(response.text)

            print result

            if response.status_code == 200 and result['response'] != "":
                ret['response'] = result['response']
                self.set_status(Response.RESULT_OK)
            else:
                print 'An error occurred while get card info'
                add_err_ko_message_to_response(ret, '카드정보 읽기 실패')
        except Exception, e:
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            self.write(json.dumps(ret))
