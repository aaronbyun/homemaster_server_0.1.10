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
from data.model.data_model import User
from sqlalchemy import func
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from err.error_handler import print_err_detail, err_dict
from response import Response
from response import add_err_message_to_response
from logger.mongo_logger import get_mongo_logger

class TestProcessHandler(tornado.web.RequestHandler):

    def get(self):

        self.set_header("Content-Type", "application/json")

        val1 = self.get_argument('val1', '')
        val2 = self.get_argument('val2', '')

        ret = {}

        try:
            ret['response'] = {'test' : '123', 'test2' : 123}
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            self.write(json.dumps(ret))
