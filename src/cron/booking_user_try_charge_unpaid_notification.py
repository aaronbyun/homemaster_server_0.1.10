#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import json
import requests
import tornado.ioloop
import tornado.web
import datetime as dt
from sqlalchemy import func, Date, cast, or_, and_
from rest.booking import booking_constant as BC
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, Master, User
from data.dao.userdao import UserDAO
from data.dao.bookingdao import BookingDAO
from data.encryption import aes_helper as aes
from err.error_handler import print_err_detail, err_dict
from payment.payment_helper import request_payment
from sender.alimtalk_sender import send_alimtalk
from utils.datetime_utils import convert_datetime_format2
from logger.mongo_logger import get_mongo_logger
from sender.jandi_sender import send_jandi

# 결제 실패건에 대해서 02:00 pm에 결제 시도
# 성공 시, 익일 시도 안함
# 실패 시, 다음 클리닝 3일 전까지 매일 02:00pm에 결제 시도
class UserTryChargeUnpaidNotifier(object):
    def __init__(self):
        pass

    def notify_try_charge_unpaid(self):
        try:
            mongo_logger = get_mongo_logger()

            userdao = UserDAO()
            bookingdao = BookingDAO()

            current_time = dt.datetime.now()
            two_weeks_before = current_time - dt.timedelta(days=28)
            two_weeks_before = two_weeks_before.date()

            print '-' * 40
            print 'try charge unpaid notification via alimtalk'
            print 'cron_time :', current_time
            print '-' * 40

            session = Session()
            result = session.query(Booking, User) \
                            .join(User, Booking.user_id == User.id) \
                            .filter(func.Date(Booking.start_time) >= two_weeks_before) \
                            .filter(Booking.cleaning_status == BC.BOOKING_COMPLETED) \
                            .filter(Booking.payment_status != BC.BOOKING_PAID) \
                            .filter(User.is_b2b == 0) \
                            .filter(Booking.source == 'hm') \
                            .order_by(Booking.start_time) \
                            .all()

            for row in result:
                if 'b2b.com' in row.User.email: # b2b 무시
                    continue

                if row.User.is_b2b == 1: # b2b 무시
                    continue

                if row.Booking.source != 'hm': # 11번가 무시
                    continue

                key = userdao.get_user_salt_by_id(row.User.id)[:16]
                crypto = aes.MyCrypto(key)

                user_id   = row.Booking.user_id
                user_name = crypto.decodeAES(row.User.name)
                phone     = crypto.decodeAES(row.User.phone)

                booking_id = row.Booking.id
                appointment_type = row.Booking.appointment_type
                cleaning_time = convert_datetime_format2(row.Booking.start_time)
                charge_price = row.Booking.price_with_task
                price = '{:,}원'.format(charge_price)

                print booking_id, user_id, user_name, cleaning_time, price

                status, try_charge, remain_days = bookingdao.is_next_booking_left_over_2days(booking_id)
                print status, try_charge, remain_days

                if status == 'FAILURE': # 다음 회차 예약 가져오기 실패. 건너 뜀
                    continue

                if try_charge: # 결제를 시도해야함
                    ret, value = request_payment(user_id, user_name, booking_id, charge_price, appointment_type)

                    if ret: # 결제 성공
                        row.Booking.payment_status = BC.BOOKING_PAID
                        session.commit()

                        print '*** success ***'

                        send_alimtalk(phone, 'notify_try_charge_unpaid_success', cleaning_time, price)
                        mongo_logger.debug('user try charge success', extra = {'dt' : current_time, 'user_id' : user_id, 'booking_id' : booking_id, 'price' : price, 'cleaning_time' : cleaning_time})
                    else: # 결제 실패
                        print '*** failed ***'
                        if remain_days == -1:
                            mongo_logger.debug('no booking remains', extra = {'dt' : current_time, 'user_id' : user_id, 'booking_id' : booking_id, 'price' : price, 'cleaning_time' : cleaning_time})

                        elif remain_days > 3: # 3일 초과로 남았으면 실패 공지
                            send_alimtalk(phone, 'notify_charge_failure', cleaning_time, price)
                            mongo_logger.debug('user try charge fail', extra = {'dt' : current_time, 'user_id' : user_id, 'booking_id' : booking_id, 'price' : price, 'cleaning_time' : cleaning_time})

                        elif remain_days >= 0: # 3일 이내면 전체 취소
                            print '*** cancel all ***'

                            bookingdao.cancel_all_upcomings(booking_id)

                            send_jandi('NEW_BOOKING', "미결제 전체 취소 알림", user_name + ' 고객님 전체 취소됨', '미결제 일시 : {}, 금액 : {}'.format(cleaning_time, price))

                            send_alimtalk(phone, 'notify_try_charge_unpaid_cancel_all', cleaning_time, price)
                            mongo_logger.debug('user try charge cancel all', extra = {'dt' : current_time, 'user_id' : user_id, 'booking_id' : booking_id, 'price' : price, 'cleaning_time' : cleaning_time})

        except Exception, e:
            print_err_detail(e)
            mongo_logger.error('failed to try charge failure', extra = {'err' : str(e)})

        finally:
            session.close()


if __name__ == '__main__':
    notifier = UserTryChargeUnpaidNotifier()
    notifier.notify_try_charge_unpaid()
