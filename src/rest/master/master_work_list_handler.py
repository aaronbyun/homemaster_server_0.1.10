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
import booking.booking_constant as BC
from response import Response
from response import add_err_message_to_response
from sqlalchemy import func, and_, or_, desc
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, User, UserAddress, Master
from data.dao.userdao import UserDAO
from data.encryption import aes_helper as aes
from utils.datetime_utils import convert_datetime_format, timedelta_to_time, time_to_minutes, convert_datetime_format2
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class MasterWorkListHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        master_id   = self.get_argument('master_id', '')

        try:
            session = Session()
            userdao = UserDAO()

            result = session.query(Master, Booking, User) \
                            .join(Booking, Master.id == Booking.master_id) \
                            .join(User, Booking.user_id == User.id) \
                            .filter(Booking.master_id == master_id) \
                            .filter(or_(Booking.cleaning_status == BC.BOOKING_UPCOMMING, Booking.cleaning_status == BC.BOOKING_STARTED, Booking.cleaning_status == BC.BOOKING_COMPLETED)) \
                            .order_by(desc(Booking.start_time)) \
                            .all()

            booking_list = []

            for row in result:
                key = userdao.get_user_salt_by_id(row.Booking.user_id)[:16]
                crypto = aes.MyCrypto(key)

                booking = {}

                booking['booking_id']       = row.Booking.id
                booking['name']             = crypto.decodeAES(row.User.name)
                booking['start_time']       = convert_datetime_format2(row.Booking.start_time)
                booking['additional_task']  = row.Booking.additional_task
                booking['price']            = row.Booking.price_with_task
                booking['status']           = row.Booking.status
                booking['cleaning_status']           = row.Booking.cleaning_status
                booking['payment_status']           = row.Booking.payment_status

                booking_list.append(booking)

            ret['response'] = booking_list
            self.set_status(Response.RESULT_OK)
            
        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()
            self.write(json.dumps(ret))