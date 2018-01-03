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

class ActiveEventHandler(tornado.web.RequestHandler):

    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        ret = {}

        mongo_logger = get_mongo_logger()

        try:
            events = []

            now = dt.datetime.now()

            session = Session()
            result = session.query(HomemasterEvent) \
                    .filter(HomemasterEvent.expire_date >= now) \
                    .order_by(HomemasterEvent.post_date) \
                    .all()

            for record in result:
                event = {}
                event['title']          = record.title
                event['description']    = record.description
                event['image_url_mo']   = record.image_url_mo
                event['image_url_web']  = record.image_url_web
                event['link']           = record.link
                event['post_date']      = convert_datetime_format2(record.post_date)
                event['expire_date']    = convert_datetime_format2(record.expire_date)

                events.append(event)

            #random.shuffle(events)

            ret['response'] = events
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()
            self.write(json.dumps(ret))
