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
import booking_constant as BC
from schedule.schedule_helper import HMScheduler
from sqlalchemy import func, or_, and_
from nptime import nptime
from utils.datetime_utils import time_to_str, timedelta_to_time, time_to_minutes
from utils.geo_utils import get_moving_time
from data.session.mysql_session import engine, Session
from data.intermediate.value_holder import IntermediateValueHolder
from data.model.data_model import Booking, UserAddress
from data.dao.userdao import UserDAO
from data.dao.addressdao import AddressDAO
from data.dao.masterdao import MasterDAO
from err.error_handler import print_err_detail, err_dict
from response import Response
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from data.intermediate.value_holder import IntermediateValueHolder
from response import add_err_message_to_response, add_err_ko_message_to_response
from sqlalchemy.exc import IntegrityError
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel
from sender.alimtalk_sender import send_alimtalk
from sender.push_sender import send_booking_schedule_updated
from utils.datetime_utils import convert_datetime_format2
from utils.time_price_info import hm_get_additional_task_time_price
try:
    from utils.secrets import MANAGERS_CALL
except ImportError:
    MANAGERS_CALL = ''


class ModifyAdditionalTaskHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        ret = {}

        booking_id                  = self.get_argument('booking_id', '')
        additional_task             = self.get_argument('additional_task', '')

        # convert parameters
        additional_task         = int(additional_task)

        # logging part
        mix = get_mixpanel()
        mongo_logger = get_mongo_logger()

        print 'modify additional task'
        print '*' * 100

        try:
            session = Session()

            booking_info = {}

            userdao     = UserDAO()
            masterdao   = MasterDAO()

            try:
                row = session.query(Booking, UserAddress) \
                             .join(UserAddress, Booking.user_id == UserAddress.user_id) \
                             .filter(Booking.addr_idx == UserAddress.user_addr_index) \
                             .filter(Booking.id == booking_id) \
                             .one()

            except NoResultFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_no_record'])
                return

            except MultipleResultsFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_multiple_record'])
                return

            print "query ok"
            print row.UserAddress.size
            print row.UserAddress.kind

            size = row.UserAddress.size
            kind = row.UserAddress.kind

            org_additional_task = row.Booking.additional_task

            org_price = row.Booking.price_with_task
            org_time  = row.Booking.estimated_end_time

            total_time, total_price = hm_get_additional_task_time_price(org_price, org_time, org_additional_task, additional_task, kind, size)
            print "total_time  : ", total_time
            print "total_price : ", total_price

            row.Booking.additional_task    = additional_task
            row.Booking.price_with_task    = total_price
            row.Booking.estimated_end_time = total_time
            row.Booking.end_time           = total_time

            session.commit()

            # other users preempt homemasters, so no homemaster available
            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)
            #add_err_message_to_response(ret, err_dict['err_homemaster_occupied'])
            return

        except Exception, e:
            session.rollback()
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)
            mongo_logger.error('error modify additional task', extra = {'booking_id' : booking_id, 'err' : str(e)})

        finally:
            session.close()
            self.write(json.dumps(ret))
