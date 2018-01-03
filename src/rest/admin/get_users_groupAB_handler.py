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
from data.model.data_model import User, UserAddress, UserDefaultAddress, Booking
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from sqlalchemy import and_
from data_analytic.mixpanel_client import Mixpanel
try:
    from utils.secrets import MX_KEY, MX_SECRET
except ImportError:
    MX_KEY = ''
    MX_SECRET = ''

class UserGroupABHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        try:
            mix = Mixpanel(MX_KEY, MX_SECRET)
            params = {}
            params['selector'] = 'properties["$predict_grade"]=="A"orproperties["$predict_grade"]=="B"'

            prediction_group = mix.request(['engage'], params)

            users = []

            for item in prediction_group['results']:
                print item['$properties']['$name'], item['$properties']['$phone']

                user_info = {}
                user_info['name']               = item['$properties']['$name']
                user_info['phone']              = item['$properties']['$phone']

                users.append(user_info)

            ret['response'] = users
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
            
        finally:
            self.write(json.dumps(ret))