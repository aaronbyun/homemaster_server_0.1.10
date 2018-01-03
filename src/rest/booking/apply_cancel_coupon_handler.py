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
import booking_constant as BC
from data.session.mysql_session import engine, Session
from data.model.data_model import UserCoupon, Booking
from err.error_handler import print_err_detail, err_dict
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from sqlalchemy.exc import IntegrityError
from logger.mongo_logger import get_mongo_logger
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
try:
    from utils.stipulation_text import PROMOTION_CODES
except ImportError:
    PROMOTION_CODES = ['']

class ApplyCancelCouponHandler(tornado.web.RequestHandler):
    def post(self):
            self.set_header("Content-Type", "application/json")
            self.set_header('Access-Control-Allow-Origin', '*')

            ret = {}

            mongo_logger = get_mongo_logger()

            booking_id  = self.get_argument('booking_id', '')

            try:
                session = Session()
                booking_record = session.query(Booking).filter(Booking.id == booking_id).one()

            except Exception, e:
                add_err_message_to_response(ret, err_dict['err_no_booking'])
                self.set_status(Response.RESULT_OK)
                print_err_detail(e)
                return

            try:
                # 이미 결제가 된 경우
                if booking_record.payment_status == BC.BOOKING_PAID:
                    self.set_status(Response.RESULT_OK)
                    add_err_message_to_response(ret, err_dict['err_already_paid'])
                    mongo_logger.error('cannot cancel coupon already paid', extra = {'booking_id' : booking_record.booking_id})
                    return

                coupon_record = session.query(UserCoupon).filter(UserCoupon.booking_id == booking_id).one()

                # cancel apply coupon

                discount_price = coupon_record.discount_price
                coupon_record.booking_id    = None
                coupon_record.used          = 0
                coupon_record.used_datetime = None
                coupon_record.service_price = 0

                # 예약 테이블에서 가격도 변경
                if discount_price <= 100: # 100보다 작으면 비율 할인
                    price = booking_record.price_with_task
                    amount_percent = 100 - discount_price
                    ratio_amount = int(price * 100 / float(amount_percent))
                    print 'ratio_amount : ',ratio_amount
                    booking_record.price_with_task = ratio_amount # 원상 복구된 가격으로 반영
                else:
                    booking_record.price_with_task += discount_price

                session.commit()

                mongo_logger.debug('coupon apply canceld', extra = {'booking_id' : booking_id})

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
