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

class ApplyPromotionCodeToUpComingBookingHandler(tornado.web.RequestHandler):
    def post(self):
            self.set_header("Content-Type", "application/json")

            ret = {}

            UNUSED      = 0
            USED        = 1
            OCCUPIED    = 2

            booking_id      = self.get_argument('booking_id')
            promotion_code  = self.get_argument('promotion_code', '')

            try:
                session = Session()
                userdao = UserDAO()
                promotiondao = PromotionDAO()

                if promotion_code in PROMOTION_CODES: # 특별 할인 코드
                    self.set_status(Response.RESULT_OK)
                    add_err_ko_message_to_response(ret, '해당 코드는 최초 예약 시에만 적용됩니다.')
                    return

                booking = session.query(Booking).filter(Booking.id == booking_id).one()
                try:
                    promotion = session.query(Promotion).filter(Promotion.promotion_code == promotion_code).one()
                except NoResultFound, e:
                    self.set_status(Response.RESULT_OK)
                    add_err_ko_message_to_response(ret, '잘못된 할인코드 입니다.')
                    return

                if promotion.used == USED:
                    session.close()
                    self.set_status(Response.RESULT_OK)
                    add_err_message_to_response(ret, err_dict['err_promotion_code_occupied'])
                    return

                price           = booking.price_with_task
                payment_status = booking.payment_status
                appointment_type  = booking.appointment_type
                user_id        = booking.user_id

                discount_amount = promotion.discount_price

                # 이미 결제가 되었다면 해당 내역 부분 취소, 아니라면 할인금액만 적용
                if booking.payment_status == BC.BOOKING_PAID:
                    # 전거래 취소 및 재결제
                    cancel_ret_code, msg = cancel_payment(user_id, booking_id, price, partial = '0')
                    if cancel_ret_code:
                        user_name = userdao.get_user_name(user_id)
                        price -= discount_amount # 할인 금액 적용
                        pay_ret_code, pay_msg = request_payment(user_id, user_name, booking_id, price, appointment_type, status='PAID')
                        if pay_ret_code:
                            booking.tid = pay_msg
                            booking.payment_status = BC.BOOKING_PAID
                        else:
                            booking.payment_status = BC.BOOKING_PAYMENT_FAILED

                        session.commit()

                print promotion_code
                if promotion_code != '' and promotion_code != 'abc' and promotion_code != 'abd' and promotion_code != 'ccccc': #test promotion code
                    promotiondao.set_promotion_code_status(promotion_code, 1, booking_id, price)

                if discount_amount <= 100: # 100보다 작으면 비율 할인
                    ratio_amount = int(price * float(discount_amount) / 100)
                    booking.price_with_task -= ratio_amount
                else:
                    booking.price_with_task -= discount_amount
                session.commit()

                ret['response'] = {'discount_price' : discount_amount}
                self.set_status(Response.RESULT_OK)

            except Exception, e:
                session.rollback()
                add_err_message_to_response(ret, err_dict['err_mysql'])
                self.set_status(Response.RESULT_SERVERERROR)
                print_err_detail(e)

            finally:
                session.close()
                self.write(json.dumps(ret))
