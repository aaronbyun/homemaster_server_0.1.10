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
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict


class DummyHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        time = {'20160112' : ['09:00', '10:00', '11:00'], 
                '20160113' : ['09:00', '10:00', '11:00', '12:00'], 
                '20160114' : ['09:00', '10:00', '11:00'], 
                '20160115' : ['09:00'], 
                '20160116' : ['09:00', '15:00', '16:00']}

        try:
            ret['response'] = time
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
            
        finally:
            self.write(json.dumps(ret))