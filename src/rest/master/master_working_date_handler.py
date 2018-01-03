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
import pytz
import calendar
import booking.booking_constant as BC
from response import Response
from response import add_err_message_to_response
from sqlalchemy import func, and_, or_, desc
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, User, UserAddress, Master, MasterScheduleByDate
from data.dao.userdao import UserDAO
from data.encryption import aes_helper as aes
from utils.datetime_utils import convert_datetime_format, timedelta_to_time, time_to_minutes, convert_datetime_format2
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class MasterWorkDateHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        master_id   = self.get_argument('master_id', '')
        year   = self.get_argument('year', 2015)
        month   = self.get_argument('month', 11)

        try:
            session = Session()
            userdao = UserDAO()

            result = session.query(Booking, Master) \
                            .join(Master, Master.id == Booking.master_id) \
                            .filter(Booking.master_id == master_id) \
                            .filter(or_(Booking.cleaning_status == BC.BOOKING_UPCOMMING, Booking.cleaning_status == BC.BOOKING_STARTED, Booking.cleaning_status == BC.BOOKING_COMPLETED)) \
                            .filter(func.year(Booking.start_time) == year) \
                            .filter(func.month(Booking.start_time) == month) \
                            .group_by(func.date(Booking.start_time)) \
                            .order_by(Booking.start_time) \
                            .all()

            working_date_list = []

            for row in result:
                work_date = dt.datetime.strftime(row.Booking.start_time, '%d')
                working_date_list.append(work_date)


            result = session.query(MasterScheduleByDate) \
                            .filter(MasterScheduleByDate.master_id == master_id) \
                            .filter(func.year(MasterScheduleByDate.date) == year) \
                            .filter(func.month(MasterScheduleByDate.date) == month) \
                            .filter(MasterScheduleByDate.active == 0) \
                            .order_by(MasterScheduleByDate.date) \
                            .all()

            dayoff_date_list = []

            for row in result:
                off_date = dt.datetime.strftime(row.date, '%d')
                dayoff_date_list.append(off_date)


            all_month_days = set([str(day+1) for day in range(calendar.monthrange(int(year), int(month))[1])])

            result = session.query(MasterScheduleByDate) \
                    .filter(MasterScheduleByDate.master_id == master_id) \
                    .filter(func.year(MasterScheduleByDate.date) == year) \
                    .filter(func.month(MasterScheduleByDate.date) == month) \
                    .order_by(MasterScheduleByDate.date) \
                    .all()

            workable_date_list = []
            for row in result:
                workable_date_list.append(str(int(dt.datetime.strftime(row.date, '%d'))))

            print all_month_days
            print workable_date_list

            not_working_date = list(all_month_days.difference(set(workable_date_list)))


            ret['response'] = {'working_date' : working_date_list,
                                'dayoff_date' : dayoff_date_list,
                                'not_working_date' : not_working_date}

            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()
            self.write(json.dumps(ret))
