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
import booking.booking_constant as BC
from sqlalchemy import and_, desc
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, User, Master
from data.dao.userdao import UserDAO
from data.encryption import aes_helper as aes
from response import Response
from response import add_err_message_to_response
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from err.error_handler import print_err_detail, err_dict
from payment.payment_helper import request_payment
from logger.mongo_logger import get_mongo_logger


class ProcessUnpaidBookingHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        booking_id         = self.get_argument('booking_id', '')

        ret = {}

        mongo_logger = get_mongo_logger()

        now = dt.datetime.now()

        try:
            session = Session()
            userdao = UserDAO()

            row = session.query(Booking) \
                        .filter(Booking.id == booking_id) \
                        .filter(Booking.cleaning_status == BC.BOOKING_COMPLETED) \
                        .filter(Booking.payment_status != BC.BOOKING_PAID) \
                        .first()

            if row:
                user_id = row.user_id
                user_name = userdao.get_user_name(user_id)
                price = row.price_with_task
                appointment_type = row.appointment_type

                ret_code, value = request_payment(user_id, user_name, booking_id, price, appointment_type)

                if ret_code:
                    row.payment_status = BC.BOOKING_PAID
                    session.commit()

                ret['response'] = {'payment_status' : str(ret_code), 'payment_result' : value}
            else:
                ret['response'] = {'payment_status' : 'no unpaid booking', 'payment_result' : ''}

            mongo_logger.debug('process unpaid booking', extra = {'booking_id' : booking_id,
                                                                 'dt' : now,
                                                                 'payment_status' : ret_code,
                                                                 'payment_result' : value})

            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
            mongo_logger.error('failed to process unpaid booking', extra = {'err' : str(e)})
        finally:
            session.close()
            self.write(json.dumps(ret))
