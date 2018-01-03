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
import pickle
import datetime as dt
import rest.booking.booking_constant as BC
from schedule.schedule_helper import HMScheduler
from nptime import nptime
from utils.datetime_utils import time_to_str, timedelta_to_time, time_to_minutes
from utils.geo_utils import get_moving_time
from data.session.mysql_session import engine, Session
from data.intermediate.value_holder import IntermediateValueHolder
from data.model.data_model import OrderID11st
from data.dao.userdao import UserDAO
from data.dao.addressdao import AddressDAO
from data.dao.masterdao import MasterDAO
from err.error_handler import print_err_detail, err_dict
from response import Response
from data.intermediate.value_holder import IntermediateValueHolder
from response import add_err_message_to_response, add_err_ko_message_to_response
from sqlalchemy.exc import IntegrityError
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel
from utils.geo_utils import get_latlng_from_address, get_geohash
from utils.time_price_info import get_time_price, get_additional_task_time_price

try:
    from utils.secrets import API_11ST_KEY
except ImportError:
    API_11ST_KEY = ''

#link_11st_hm
class LinkHomemaster11stBookingHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        booking_id  = self.get_argument('booking_id', '')
        div_no      = self.get_argument('div_no', '')

        ret = {}
        mongo_logger = get_mongo_logger()

        try:
            session = Session()

            order_11st = OrderID11st(booking_id = booking_id, div_no = div_no,
                                    datetime = dt.datetime.now())
            session.add(order_11st)
            session.commit()

            ret['response'] = Response.SUCCESS
            mongo_logger.debug('link hm 11st', extra = {'div_no' : div_no, 'booking_id' : booking_id})

            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)
            mongo_logger.error('failed tolink hm 11st',
                        extra = {'div_no' : div_no, 'booking_id' : booking_id})

        finally:
            session.close()
            self.write(json.dumps(ret))
