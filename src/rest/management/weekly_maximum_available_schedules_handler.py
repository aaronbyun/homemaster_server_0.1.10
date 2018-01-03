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
import datetime as dt
from rest.booking import booking_constant as BC
from data.dao.userdao import UserDAO
from data.dao.bookingdao import BookingDAO
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, Master, UserPaymentRecord, Promotion, MasterPoint, User, UserAddress
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import func, and_, not_
from err.error_handler import print_err_detail, err_dict
from response import Response
from response import add_err_message_to_response
from data.encryption import aes_helper as aes
from schedule.available_schedule_helper import HMAvailableScheduler

class WeeklyMaximumAvailableScheduleHandler(tornado.web.RequestHandler):
    def subs_time(self, start, end):
        start_hour = int(start.split(':')[0])
        start_min  = int(start.split(':')[1])

        end_hour = int(end.split(':')[0])
        end_min  = int(end.split(':')[1])

        sub_min = (end_hour * 60 + end_min) - (start_hour * 60 + start_min)

        return sub_min


    def get_available_count(self, time_list, taking_time):
        start = 0

        count = 1
        if not time_list:
            count = 0

        for i in range(1, len(time_list)):

            if self.subs_time(time_list[start], time_list[i]) >= taking_time + 60: # minutes
                start = i
                count += 1

        print time_list, count
        return count

    def get_total_count(self, available_slots, taking_time, startkey, endkey):
        total_count = 0

        for day in available_slots:
            if startkey <= day <= endkey:
                master_available_slots = available_slots[day]

                for master_id in master_available_slots:
                    time_list = master_available_slots[master_id]

                    total_count += self.get_available_count(time_list, taking_time)

        return total_count

    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        ret = {}

        try:
            session = Session()
            scheduler = HMAvailableScheduler()

            SATURDAY = 5
            now = dt.datetime.now()
            offset = (now.weekday() - SATURDAY) % 7

            last_saturday = (now - dt.timedelta(days=offset)).date()
            this_friday = last_saturday + dt.timedelta(days=6)

            appointment_type = 4
            taking_time = 300

            # min
            available_slots = scheduler.get_available_slots(appointment_type,
                                taking_time, False, False)
            total_min_count = self.get_total_count(available_slots, taking_time,
                                dt.datetime.strftime(last_saturday, '%Y%m%d'),
                                dt.datetime.strftime(this_friday, '%Y%m%d'))

            # next min
            available_slots = scheduler.get_available_slots(appointment_type,
                                taking_time, False, False)
            next_total_min_count = self.get_total_count(available_slots, taking_time,
                            dt.datetime.strftime(last_saturday + dt.timedelta(days = 7), '%Y%m%d'),
                            dt.datetime.strftime(this_friday + dt.timedelta(days = 7), '%Y%m%d'))

            appointment_type = 0
            taking_time = 180

            # max
            available_slots = scheduler.get_available_slots(appointment_type,
                                taking_time, False, False)
            total_max_count = self.get_total_count(available_slots, taking_time,
                                dt.datetime.strftime(last_saturday, '%Y%m%d'),
                                dt.datetime.strftime(this_friday, '%Y%m%d'))

            # next max
            available_slots = scheduler.get_available_slots(appointment_type,
                                taking_time, False, False)
            next_total_max_count = self.get_total_count(available_slots, taking_time,
                            dt.datetime.strftime(last_saturday + dt.timedelta(days = 7), '%Y%m%d'),
                            dt.datetime.strftime(this_friday + dt.timedelta(days = 7), '%Y%m%d'))


            # this week expected count
            this_week_count = session.query(Booking) \
                    .filter(Booking.cleaning_status != BC.BOOKING_CANCELED) \
                    .filter(func.date(Booking.start_time) >= last_saturday) \
                    .filter(func.date(Booking.start_time) <= this_friday) \
                    .count()

            next_week_count = session.query(Booking) \
                    .filter(Booking.cleaning_status != BC.BOOKING_CANCELED) \
                    .filter(func.date(Booking.start_time) >= last_saturday + dt.timedelta(days = 7)) \
                    .filter(func.date(Booking.start_time) <= this_friday + dt.timedelta(days = 7)) \
                    .count()

            next_week_count2 = session.query(Booking) \
                    .filter(Booking.cleaning_status != BC.BOOKING_CANCELED) \
                    .filter(func.date(Booking.start_time) >= last_saturday + dt.timedelta(days = 14)) \
                    .filter(func.date(Booking.start_time) <= this_friday + dt.timedelta(days = 14)) \
                    .count()

            next_week_count3 = session.query(Booking) \
                    .filter(Booking.cleaning_status != BC.BOOKING_CANCELED) \
                    .filter(func.date(Booking.start_time) >= last_saturday + dt.timedelta(days = 21)) \
                    .filter(func.date(Booking.start_time) <= this_friday + dt.timedelta(days = 21)) \
                    .count()

            print this_week_count
            print next_week_count

            ret['response'] = {'min_available_count' : [total_min_count + this_week_count, next_total_min_count + next_week_count],
                                'max_available_count' : [total_max_count + this_week_count, next_total_max_count + next_week_count],
                                'current_count' : [this_week_count, next_week_count, next_week_count2, next_week_count3]}

            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()

            self.write(json.dumps(ret))
