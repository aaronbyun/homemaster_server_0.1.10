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
from sender.push_sender import send_24hours_ahead_notification, send_24hours_ahead_price_notification
from sender.alimtalk_sender import send_alimtalk

# 24시간 전 고객에 클리닝 알림
# 24에서 48로 변경됨..클래스 이름은 그대로 두는 것으로 결정..
class User24AheadNotifier(object):
    def __init__(self):
        pass 

    # 매일 저녁 9시 내일 스케쥴에 대해 공지 해줌
    def notify_24hours_ahead(self):
        try:
            userdao = UserDAO()
            
            current_time = dt.datetime.now()

            print '-' * 40
            print 'push before 48 hours'
            print 'current_time :', current_time

            hour = current_time.hour
            minute = 30 if current_time.minute >= 30 else 0 

            current_time = current_time + dt.timedelta(days=2)
            cron_time = current_time.replace(hour=hour, minute=minute, second = 0, microsecond=0)

            print 'cron_time :', cron_time
            print '-' * 40

            session = Session()
            result = session.query(Booking, Master, User, UserPushKey) \
                            .join(Master, Booking.master_id == Master.id) \
                            .join(User, Booking.user_id == User.id) \
                            .outerjoin(UserPushKey, User.id == UserPushKey.user_id) \
                            .filter(or_(Booking.cleaning_status == BC.BOOKING_UPCOMMING, Booking.cleaning_status == BC.BOOKING_STARTED)) \
                            .filter(func.date(Booking.start_time) == cron_time.date()) \
                            .filter(func.HOUR(Booking.start_time) == cron_time.time().hour) \
                            .filter(func.MINUTE(Booking.start_time) == cron_time.time().minute) \
                            .all()


            for row in result:

                key = userdao.get_user_salt_by_id(row.User.id)[:16]
                crypto = aes.MyCrypto(key)

                booking_id = row.Booking.id
                pushkey = row.UserPushKey.pushkey if row.UserPushKey != None else ''
                user_name = crypto.decodeAES(row.User.name)
                phone   = crypto.decodeAES(row.User.phone)
                master_name = row.Master.name
                devicetype = row.User.devicetype
                price = row.Booking.price_with_task

                print 'push to', user_name, master_name, booking_id
                print pushkey

                if devicetype != 'android':
                    pushkey = crypto.decodeAES(row.User.phone)
                    send_24hours_ahead_price_notification(devicetype, [pushkey], booking_id, user_name, master_name, price) # 자동결제 대상이 아닌 고객에게 고지를 위해 계좌번호 문자로 발송함.
                else:
                    send_24hours_ahead_notification(devicetype, [pushkey], booking_id, user_name, master_name)

                send_alimtalk(phone, 'noti_48', user_name, master_name)

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()


if __name__ == '__main__':
    notifier = User24AheadNotifier()
    notifier.notify_24hours_ahead()