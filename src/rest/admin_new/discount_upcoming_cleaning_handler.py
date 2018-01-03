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
import datetime as dt
import pytz
import rest.booking.booking_constant as BC
from data.session.mysql_session import engine, Session
from data.model.data_model import Promotion, EventPromotion, Booking
from data.dao.userdao import UserDAO
from data.dao.promotiondao import PromotionDAO
from err.error_handler import print_err_detail, err_dict
from payment.payment_helper import request_payment, cancel_payment
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
try:
    from utils.stipulation_text import PROMOTION_CODES
except ImportError:
    PROMOTION_CODES = ['']

class DiscountUpcomingCleaningHandler(tornado.web.RequestHandler):
    def post(self):
            self.set_header("Content-Type", "application/json")
            self.set_header('Access-Control-Allow-Origin', '*')

            ret = {}

            booking_id  = self.get_argument('booking_id', '')
            amount      = self.get_argument('amount', '')

            amount = int(amount)

            try:
                session = Session()
                userdao = UserDAO()

                count = session.query(Promotion) \
                            .filter(Promotion.booking_id == booking_id) \
                            .count()

                if count > 0:
                    self.set_status(Response.RESULT_OK)
                    add_err_ko_message_to_response(ret, '이미 할인이 적용된 예약입니다.')
                    return

                row = session.query(Promotion) \
                            .filter(Promotion.used == 0) \
                            .filter(Promotion.discount_price == amount) \
                            .filter(Promotion.source == 'hm') \
                            .first()

                booking_row = session.query(Booking) \
                                    .filter(Booking.id == booking_id) \
                                    .one()

                if row == None:
                    self.set_status(Response.RESULT_OK)
                    add_err_ko_message_to_response(ret, '해당 쿠폰이 존재하지 않습니다.')
                    return

                if booking_row.payment_status != 0:
                    self.set_status(Response.RESULT_OK)
                    add_err_ko_message_to_response(ret, '결제되지 않은 예약에 대해서만 할인 적용이 가능합니다.')
                    return

                if booking_row.cleaning_status != 0:
                    self.set_status(Response.RESULT_OK)
                    add_err_ko_message_to_response(ret, '다가오는 클리닝만 할일 적용이 가능합니다.')
                    return


                row.booking_id = booking_id
                row.used = 1
                row.service_price = booking_row.price_with_task
                row.used_datetime = dt.datetime.now()

                if amount <= 100:
                    discount_price = int(booking_row.price_with_task * float(amount) / 100)
                    booking_row.price_with_task -= discount_price

                else:
                    booking_row.price_with_task -= amount

                session.commit()

                ret['response'] = Response.SUCCESS
                self.set_status(Response.RESULT_OK)

            except Exception, e:
                session.rollback()
                add_err_message_to_response(ret, err_dict['err_mysql'])
                self.set_status(Response.RESULT_SERVERERROR)
                print_err_detail(e)

            finally:
                session.close()
                self.write(json.dumps(ret))
