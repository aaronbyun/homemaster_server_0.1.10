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
from utils.datetime_utils import time_to_str, timedelta_to_time, time_to_minutes,dow_convert
from utils.geo_utils import get_moving_time
from data.session.mysql_session import engine, Session
from data.intermediate.value_holder import IntermediateValueHolder
from data.model.data_model import Booking,Master
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

from payment.payment_helper import request_payment, cancel_payment

#Class to change master in the booking
class MasterHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        ret = {}

        booking_id                  = self.get_argument('booking_id', '')
        change_all                  = self.get_argument('change_all','false')
        master_id                   = self.get_argument('master_id','')

        change_all = False if (change_all.strip() == 'false')  else True
        mongo_logger = get_mongo_logger()

        try:
            session = Session()
            bookingrow = session.query(Booking).filter(Booking.id == booking_id).one()
            org_master_id = bookingrow.master_id
            bookingrow.master_id = master_id
            bookingrow.is_master_changed = 1
            org_start = bookingrow.start_time
            apply_to_all_behind = 1 if change_all is True else 0
            mongo_logger.debug('update logs', extra = {'user_id' : bookingrow.user_id,
                            'booking_id' : booking_id, 'apply_to_all_behind' : apply_to_all_behind,
                            'org_master_id' : org_master_id, 'changed_master_id' : master_id,
                            'by_manager' : 1})
            if change_all:
                bookingrow.is_master_changed = 0
                booking_data = session.query(Booking)\
                                      .filter((Booking.request_id == bookingrow.request_id)
                                      &(Booking.start_time > org_start))\
                                      .update({'master_id': master_id,
                                                'is_master_changed': 0 })
                session.query(Booking)\
                                      .filter((Booking.request_id == bookingrow.request_id)
                                      &(Booking.start_time < org_start))\
                                      .update({'is_master_changed': 1 })

                booking_rows = session.query(Booking.id)\
                                      .filter((Booking.request_id == bookingrow.request_id)
                                      &(Booking.start_time > org_start))\
                                      .all()

                for row in booking_rows:
                    mongo_logger.debug('update logs', extra = {'user_id' : bookingrow.user_id,
                                    'booking_id' : row.id, 'apply_to_all_behind' : apply_to_all_behind,
                                    'org_master_id' : org_master_id, 'changed_master_id' : master_id,
                                    'by_manager' : 1})

            session.commit()

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

        except Exception , e:
            session.rollback()
            ret['response'] = e
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_id_not_found'])

        finally:
            session.close()
            self.write(json.dumps(ret))
