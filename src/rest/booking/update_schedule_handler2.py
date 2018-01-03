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
from utils.datetime_utils import time_to_str, timedelta_to_time, time_to_minutes,dow_convert, date_convert
from utils.geo_utils import get_moving_time
from data.session.mysql_session import engine, Session
from data.intermediate.value_holder import IntermediateValueHolder
from data.model.data_model import UserPaymentRecord, Booking, UserDefaultAddress, UserDefaultCard
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


class UpdateScheduleHandler2(tornado.web.RequestHandler):


    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        ret = {}

        booking_id                  = self.get_argument('booking_id', '')
        start_time                  = self.get_argument('start_time', '')
        end_time                    = self.get_argument('end_time','')
        change_all                  = self.get_argument('change_all',False)
        mongo_logger = get_mongo_logger()

        try:
            change_all = False if (change_all.strip() == 'false')  else True
            session = Session()
            bookingrow = session.query(Booking)\
                                .filter(Booking.id == booking_id)\
                                .one()
            #Variable Setting
            start_time = dt.datetime.strptime(start_time,'%Y-%m-%d %H:%M')
            end_time = dt.datetime.strptime(end_time,'%Y-%m-%d %H:%M')
            org_start = bookingrow.start_time
            date_diff = start_time.date() - org_start.date()
            day_to_end = (start_time.weekday() >= 5) and (org_start.weekday() < 5)
            end_to_day = (start_time.weekday() < 5 )  and (org_start.weekday() >= 5)

            #Change first row
            bookingrow.start_time = start_time
            bookingrow.end_time = end_time
            bookingrow.estimated_end_time = end_time
            org_price = bookingrow.price
            apply_to_all_behind = 1 if change_all is True else 0
            if day_to_end:
                bookingrow.price = bookingrow.price + 10000
                bookingrow.price_with_task = bookingrow.price_with_task + 10000
            elif end_to_day:
                bookingrow.price = bookingrow.price - 10000
                bookingrow.price_with_task = bookingrow.price_with_task - 10000

            mongo_logger.debug('update logs', extra = {'user_id' : bookingrow.user_id,
                                        'org_start_time' : org_start, 'changed_start_time' : bookingrow.start_time,
                                        'org_price' : org_price, 'changed_price' : bookingrow.price,
                                        'booking_id' : booking_id, 'apply_to_all_behind' : apply_to_all_behind,
                                        'by_manager' : 1})

            #Change all rows
            if change_all :
                #change org_time of first row
                bookingrow.org_start_time = start_time

                #change subsequent row
                booking_data = session.query(Booking)\
                                      .filter((Booking.request_id == bookingrow.request_id)
                                      &(Booking.start_time > org_start)
                                      &(Booking.id != booking_id))\
                                      .order_by(Booking.start_time)\
                                      .all()
                for row in booking_data:
                    org_price = row.price
                    org_start = row.start_time
                    row.start_time = row.start_time.replace(hour = start_time.hour,minute = start_time.minute) + date_diff
                    row.org_start_time = row.start_time
                    row.end_time = row.end_time.replace(hour = end_time.hour,minute = end_time.minute) + date_diff
                    row.estimated_end_time = row.estimated_end_time.replace(hour = end_time.hour,minute = end_time.minute) + date_diff
                    if day_to_end:
                        row.price = row.price + 10000
                        row.price_with_task = row.price_with_task + 10000
                    elif end_to_day:
                        row.price = row.price - 10000
                        row.price_with_task = row.price_with_task - 10000
                    mongo_logger.debug('update logs', extra = {'user_id' : row.user_id,
                                                'org_start_time' : org_start, 'changed_start_time' : row.start_time,
                                                'org_price' : org_start, 'changed_price' : row.price,
                                                'booking_id' : row.id, 'apply_to_all_behind' : apply_to_all_behind,
                                                'by_manager' : 1})




            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)
            session.commit()
        except Exception , e:
            session.rollback()
            ret['response'] = e
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()
            self.write(json.dumps(ret))
