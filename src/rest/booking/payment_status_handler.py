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

class PaymentStatusHandler(tornado.web.RequestHandler):


    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        ret = {}

        booking_id                  = self.get_argument('booking_id', '')
        payment_status              = self.get_argument('payment_status','')
        change_all                  = self.get_argument('change_all','false')

        try:
            session = Session()
            payment_status = int(payment_status)
            change_all = False if (change_all.strip() == 'false')  else True
            bookingrow = session.query(Booking)\
                                .filter(Booking.id == booking_id)\
                                .first()
            org_start = bookingrow.start_time
            bookingrow.payment_status = payment_status
            if change_all :
                booking_data = session.query(Booking)\
                                      .filter((Booking.request_id == bookingrow.request_id)
                                      &(Booking.start_time > org_start))\
                                      .update({'payment_status':payment_status})

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)
            session.commit()
        except Exception, e:
            session.rollback()
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()
            self.write(json.dumps(ret))
