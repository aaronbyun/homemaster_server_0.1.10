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
from data.model.data_model import Booking, Master, User, MasterPushKey
from data.dao.userdao import UserDAO
from data.encryption import aes_helper as aes
from err.error_handler import print_err_detail, err_dict
from payment.payment_helper import request_payment
from sender.push_sender import send_master_before_complete_notification
from sender.alimtalk_sender import send_alimtalk
from utils.datetime_utils import convert_datetime_format4

# 30분전 마스터님에 클리닝 알림
class Master30minsAheadNotifier(object):
    def __init__(self):
        pass

    # 매일 저녁 9시 내일 스케쥴에 대해 공지 해줌
    def notify(self):
        try:
            userdao = UserDAO()

            current_time = dt.datetime.now()

            print '-' * 40
            print 'push before 24 hours'
            print 'current_time :', current_time

            hour = current_time.hour
            minute = 30 if current_time.minute >= 30 else 0

            if minute == 30:
                hour += 1
                minute = 0
            else:
                minute = 30

            cron_time = current_time.replace(hour=hour, minute=minute, second = 0, microsecond=0)

            print 'cron_time :', cron_time
            print '-' * 40

            session = Session()
            result = session.query(Booking, Master, MasterPushKey, User) \
                            .join(Master, Booking.master_id == Master.id) \
                            .join(MasterPushKey, Master.id == MasterPushKey.master_id) \
                            .join(User, Booking.user_id == User.id) \
                            .filter(or_(Booking.cleaning_status == BC.BOOKING_UPCOMMING, Booking.cleaning_status == BC.BOOKING_STARTED)) \
                            .filter(func.date(Booking.estimated_end_time) == cron_time.date()) \
                            .filter(func.HOUR(Booking.estimated_end_time) == cron_time.time().hour) \
                            .filter(func.MINUTE(Booking.estimated_end_time) == cron_time.time().minute) \
                            .all()


            for row in result:

                key = userdao.get_user_salt_by_id(row.User.id)[:16]
                crypto = aes.MyCrypto(key)

                if row.Master.id == 'da2a1f50-fd36-40bf-8460-55b3e1b2c459':
                    continue

                booking_id = row.Booking.id
                pushkey = row.MasterPushKey.pushkey if row.MasterPushKey != None else ''
                master_name = row.Master.name

                start_time = row.Booking.start_time
                time_str = convert_datetime_format4(start_time)

                print 'push to', master_name, booking_id
                print pushkey

                send_master_before_complete_notification('android', [pushkey], booking_id, master_name)

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()


if __name__ == '__main__':
    notifier = Master30minsAheadNotifier()
    notifier.notify()
