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
import booking_constant as BC
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking
from data.dao.masterdao import MasterDAO
from data.dao.userdao import UserDAO
from data.dao.addressdao import AddressDAO
from data.intermediate.value_holder import IntermediateValueHolder
from utils.datetime_utils import convert_datetime_format, time_to_minutes, timedelta_to_time
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from err.error_handler import print_err_detail, err_dict
from utils.stipulation_text import BOOKING_TYPE_DICT, BOOKING_UPDATE_TEXT, BOOKING_TEXT_SUBJECT
from utils.time_price_info import get_window_time_price, get_basic_time_price
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import or_
from payment.payment_helper import cancel_payment, request_payment
from sender.sms_sender import send_updated_text
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel

class RequestTimePriceWebHandler(tornado.web.RequestHandler):
    def get(self):
        ret = {}

        try:
            self.set_header("Content-Type", "application/json")
            self.set_header('Access-Control-Allow-Origin', '*')

            size             = self.get_argument('size', '')
            _type            = self.get_argument('type', '')

            size             = int(size)
            _type            = int(_type)

            time_price_list = get_basic_time_price(_type, size)
            window_price, window_time = get_window_time_price(_type, size)

            ret['response'] = {'basic': time_price_list, 'window_price' : window_price, 'window_time': window_time }
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            self.write(json.dumps(ret))
