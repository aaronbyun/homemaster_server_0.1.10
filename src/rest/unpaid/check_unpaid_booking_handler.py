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
from data.model.data_model import Booking, User, Master, UserCard
from data.dao.userdao import UserDAO
from data.encryption import aes_helper as aes
from response import Response
from response import add_err_message_to_response
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from err.error_handler import print_err_detail, err_dict
from utils.datetime_utils import convert_datetime_format2
from logger.mongo_logger import get_mongo_logger


class CheckUnpaidBookingHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        user_id         = self.get_argument('user_id', '')

        ret = {}

        mongo_logger = get_mongo_logger()

        try:
            now = dt.datetime.now()
            session = Session()

            row = session.query(Booking, UserCard) \
                        .outerjoin(UserCard, and_(Booking.user_id == UserCard.user_id, Booking.card_idx == UserCard.user_card_index)) \
                        .filter(Booking.user_id == user_id) \
                        .filter(Booking.start_time < now) \
                        .filter(Booking.cleaning_status == BC.BOOKING_COMPLETED) \
                        .filter(Booking.payment_status != BC.BOOKING_PAID) \
                        .order_by(desc(Booking.start_time)) \
                        .first()

            if row:
                booking_id = row.Booking.id
                cleaning_price = row.Booking.price_with_task
                cleaning_time = convert_datetime_format2(row.Booking.start_time)
                card_alias   = row.UserCard.card_alias if row.UserCard != None else ''

                ret['response'] = {'unpaid_booking' : True,
                                   'card_alias' : card_alias,
                                   'booking_id' : booking_id,
                                   'cleaning_price' : cleaning_price,
                                   'cleaning_time' : cleaning_time}

                mongo_logger.debug('check unpaid booking', extra = {'user_id' : user_id,
                                                                    'dt' : now,
                                                                    'unpaid_booking' : True,
                                                                    'booking_id' : booking_id,
                                                                    'cleaning_price' : cleaning_price,
                                                                    'cleaning_time' : cleaning_time})
            else:
                ret['response'] = {'unpaid_booking' : False}

                mongo_logger.debug('check unpaid booking', extra = {'user_id' : user_id,
                                                                    'dt' : now,
                                                                    'unpaid_booking' : False})

            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
            mongo_logger.error('failed to check unpaid booking', extra = {'err' : str(e)})
        finally:
            session.close()
            self.write(json.dumps(ret))
