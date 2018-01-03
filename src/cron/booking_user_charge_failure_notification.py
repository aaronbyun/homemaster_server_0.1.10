#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import json
import tornado.ioloop
import tornado.web
import datetime as dt
from sqlalchemy import func, Date, cast, or_, and_
from rest.booking import booking_constant as BC
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, Master, User, UserPushKey
from data.dao.userdao import UserDAO
from data.encryption import aes_helper as aes
from err.error_handler import print_err_detail, err_dict
from payment.payment_helper import request_payment
from utils.datetime_utils import convert_datetime_format2
from sender.alimtalk_sender import send_alimtalk
from logger.mongo_logger import get_mongo_logger

# 클리닝 완료 예정 시각에 결제 실패 알림
class UserChargeFailureNotifier(object):
    def __init__(self):
        pass

    def notify_charge_failure(self):
        try:
            mongo_logger = get_mongo_logger()

            userdao = UserDAO()

            current_time = dt.datetime.now()

            print '-' * 40
            print 'charge failure notification via alimtalk'
            print 'current_time :', current_time

            hour = current_time.hour
            minute = 30 if current_time.minute >= 30 else 0

            cron_time = current_time.replace(hour=hour, minute=minute, second = 0, microsecond=0)

            print 'cron_time :', cron_time
            print '-' * 40

            session = Session()
            result = session.query(Booking, User) \
                            .join(User, Booking.user_id == User.id) \
                            .filter(Booking.cleaning_status == BC.BOOKING_COMPLETED) \
                            .filter(Booking.payment_status != BC.BOOKING_PAID) \
                            .filter(func.date(Booking.estimated_end_time) == cron_time.date()) \
                            .filter(func.HOUR(Booking.estimated_end_time) == cron_time.time().hour) \
                            .filter(func.MINUTE(Booking.estimated_end_time) == cron_time.time().minute) \
                            .filter(User.is_b2b == 0) \
                            .filter(Booking.source == 'hm') \
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

                user_id = row.User.id
                phone   = crypto.decodeAES(row.User.phone)

                cleaning_time = convert_datetime_format2(row.Booking.start_time)
                price = '{:,}원'.format(row.Booking.price_with_task)

                try:
                    send_alimtalk(phone, 'notify_charge_failure', cleaning_time, price)

                    mongo_logger.debug('user charge failure', extra = {'dt' : current_time, 'user_id' : user_id, 'price' : price, 'cleaning_time' : cleaning_time})
                except Exception, e:
                    mongo_logger.error('err user charge failure', extra = {'dt' : current_time, 'user_id' : user_id, 'price' : price, 'cleaning_time' : cleaning_time})

        except Exception, e:
            print_err_detail(e)
            mongo_logger.error('failed to user charge failure', extra = {'err' : str(e)})

        finally:
            session.close()


if __name__ == '__main__':
    notifier = UserChargeFailureNotifier()
    notifier.notify_charge_failure()
