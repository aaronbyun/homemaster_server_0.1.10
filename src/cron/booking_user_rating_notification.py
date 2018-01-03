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
from data.model.data_model import Booking, User, UserPushKey
from data.dao.userdao import UserDAO
from data.encryption import aes_helper as aes
from err.error_handler import print_err_detail, err_dict
from payment.payment_helper import request_payment
from sender.push_sender import send_rating_notification

# 매일 9시 고객에게 오늘 클리닝 평가 push

class UserRatingNotifier(object):
    def __init__(self):
        pass

    # 매일 저녁 9시 내일 스케쥴에 대해 공지 해줌
    def notify(self):
        try:
            userdao = UserDAO()

            current_date = dt.datetime.now().date()

            print current_date

            session = Session()
            result = session.query(Booking, User, UserPushKey) \
                        .join(User, Booking.user_id == User.id) \
                        .join(UserPushKey, User.id == UserPushKey.user_id) \
                        .filter(func.date(Booking.start_time) == current_date) \
                        .filter(Booking.cleaning_status == BC.BOOKING_COMPLETED) \
                        .all()

            for row in result:
                key = userdao.get_user_salt_by_id(row.User.id)[:16]
                crypto = aes.MyCrypto(key)

                booking_id = row.Booking.id
                user_name  = crypto.decodeAES(row.User.name)
                pushkey    = row.UserPushKey.pushkey
                devicetype = row.User.devicetype

                if row.Booking.havereview == 0: # review 하지 않은 사용자에게만 보냄
                    print 'rating push to ', user_name, booking_id

                    if devicetype != 'android':
                        pushkey = crypto.decodeAES(row.User.phone)

                    send_rating_notification(devicetype, [pushkey], booking_id, user_name)

            print 'notified to users for rating successfully...', dt.datetime.now()

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()


if __name__ == '__main__':
    notifier = UserRatingNotifier()
    notifier.notify()
