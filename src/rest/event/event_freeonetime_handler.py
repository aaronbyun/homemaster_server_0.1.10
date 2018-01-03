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
import redis
import datetime as dt
import pytz
import random
from response import Response
from response import add_err_message_to_response
from data.session.mysql_session import engine, Session
from data.model.data_model import HomemasterEvent
from data.dao.userdao import UserDAO
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from data.encryption import aes_helper as aes
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel
from utils.datetime_utils import convert_datetime_format2

try:
    from utils.secrets import REDIS_HOST, REDIS_PORT, REDIS_PWD
except ImportError:
    REDIS_HOST = 'localhost'
    REDIS_PORT = 6379
    REDIS_PWD = ''

class FreeOneTimeRegularCleaningHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        ret = {}

        mongo_logger = get_mongo_logger()

        try:
            now = dt.datetime.now()
            r = redis.Redis(host = REDIS_HOST, port = REDIS_PORT, password = REDIS_PWD)

            event_on = r.get('free_event')

            event = True
            if event_on == None or event_on != 'on':
                event = False

            ret['response'] = event
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            self.write(json.dumps(ret))
