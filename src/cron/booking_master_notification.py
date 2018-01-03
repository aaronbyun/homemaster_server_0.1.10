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
from data.model.data_model import Booking, Master
from err.error_handler import print_err_detail, err_dict
from payment.payment_helper import request_payment
from sender.sms_sender import send_24hours_ahead_reminder


# 매일 9시 홈마스터에 내일 클리닝 

class MasterNotifier(object):
    def __init__(self):
        pass 

    # 매일 저녁 9시 내일 스케쥴에 대해 공지 해줌
    def notify_24hours_ahead(self):
        try:
            print 'master notifier started...'
            current_date = dt.datetime.now()

            print current_date

            tomorrow = current_date + dt.timedelta(days=1)
            tomorrow = tomorrow.date()

            print tomorrow

            session = Session()
            result = session.query(Booking.master_id, Master.phone, Master.name, func.count(Booking.master_id)) \
                .join(Master, Booking.master_id == Master.id) \
                .filter(func.date(Booking.start_time) == tomorrow) \
                .group_by(Booking.master_id) \
                .all()

            for row in result:
                master_phone = str(row[1])
                master_name  = str(row[2])
                no_jobs      = str(int(row[3]))

                print master_phone, master_name, no_jobs

                send_24hours_ahead_reminder(master_phone, master_name, no_jobs)

            print 'notified to masters successfully...'

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()


if __name__ == '__main__':
    notifier = MasterNotifier()
    notifier.notify_24hours_ahead()