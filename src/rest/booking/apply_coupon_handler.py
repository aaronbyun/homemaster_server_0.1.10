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

class ApplyCouponHandler(tornado.web.RequestHandler):
    def post(self):
            self.set_header("Content-Type", "application/json")
            self.set_header('Access-Control-Allow-Origin', '*')

            ret = {}

            mongo_logger = get_mongo_logger()

            booking_id  = self.get_argument('booking_id', '')
            coupon_id   = self.get_argument('coupon_id', '')

            try:
                session = Session()
                coupon_record = session.query(UserCoupon).filter(UserCoupon.id == coupon_id).one()

            except Exception, e:
                add_err_message_to_response(ret, err_dict['err_no_coupon'])
                self.set_status(Response.RESULT_OK)
                print_err_detail(e)
                return

            try:
                booking_record = session.query(Booking).filter(Booking.id == booking_id).one()

            except Exception, e:
                add_err_message_to_response(ret, err_dict['err_no_booking'])
                self.set_status(Response.RESULT_OK)
                print_err_detail(e)
                return

            try:
                booking_user_id = booking_record.user_id
                coupon_user_id  = coupon_record.user_id

                # 다른 사용자의 쿠폰일 경우
                if booking_user_id != coupon_user_id:
                    self.set_status(Response.RESULT_OK)
                    add_err_message_to_response(ret, err_dict['err_user_id_unmatch'])
                    mongo_logger.error('user_ids are not same when apply coupon', extra = {'booking_user_id' : booking_user_id, 'coupon_user_id' : coupon_user_id})
                    return

                # 이미 쿠폰이 사용된 경우
                print coupon_record.booking_id, coupon_record.used
                if coupon_record.booking_id != None or \
                    coupon_record.used != 0:

                    self.set_status(Response.RESULT_OK)
                    add_err_message_to_response(ret, err_dict['err_coupon_already_applied'])
                    mongo_logger.error('coupon is already applied to another booking', extra = {'booking_id' : coupon_record.booking_id})
                    return

                # 이미 결제가 된 경우
                if booking_record.payment_status == BC.BOOKING_PAID:
                    self.set_status(Response.RESULT_OK)
                    add_err_message_to_response(ret, err_dict['err_already_paid'])
                    mongo_logger.error('copun is applied to already paid', extra = {'booking_id' : booking_record.booking_id})
                    return

                # apply coupon
                discount_price              = coupon_record.discount_price
                coupon_record.booking_id    = booking_id
                coupon_record.used          = 1
                coupon_record.used_datetime     = dt.datetime.now()
                coupon_record.service_price = booking_record.price_with_task

                # 예약 테이블에서 가격도 변경
                if discount_price <= 100: # 100보다 작으면 비율 할인
                    price = booking_record.price_with_task
                    ratio_amount = int(price * float(discount_price) / 100)
                    booking_record.price_with_task -= ratio_amount
                else:
                    booking_record.price_with_task -= discount_price


                session.commit()

                mongo_logger.debug('coupon applied', extra = {'booking_id' : booking_id, 'coupon_id' : coupon_id})

                ret['response'] = {'discount_price' : discount_price}
                self.set_status(Response.RESULT_OK)

            except Exception, e:
                session.rollback()
                add_err_message_to_response(ret, err_dict['err_mysql'])
                self.set_status(Response.RESULT_SERVERERROR)
                print_err_detail(e)

            finally:
                session.close()
                self.write(json.dumps(ret))
