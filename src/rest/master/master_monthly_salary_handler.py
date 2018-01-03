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
from data.dao.userdao import UserDAO
from data.dao.bookingdao import BookingDAO
from data.dao.masterdao import MasterDAO
from rest.booking import booking_constant as BC
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, Master, User, UserAddress
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import func, and_, desc, or_
from sqlalchemy.sql.expression import text
from err.error_handler import print_err_detail, err_dict
from response import Response
from response import add_err_message_to_response
from master_constant import master_fee_rate_dict
from utils.datetime_utils import get_month_day_range

class MasterMonthlySalaryHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        master_id = self.get_argument('master_id', '')
        year      = self.get_argument('yyyy', 2016)
        month     = self.get_argument('mm', 9)

        ret = {}

        try:
            session = Session()
            masterdao = MasterDAO()
            userdao = UserDAO()
            bookingdao = BookingDAO()

            CANCELED_RATE = 0.5

            year = int(year)
            month = int(month)

            first_day, last_day = get_month_day_range(dt.date(year, month, 7))

            result = session.query(Booking, Master, User, UserAddress) \
                            .join(Master, Booking.master_id == Master.id) \
                            .join(User, Booking.user_id == User.id) \
                            .join(UserAddress, and_(Booking.user_id == UserAddress.user_id, Booking.addr_idx == UserAddress.user_addr_index)) \
                            .filter(and_(func.date(Booking.start_time) >= first_day, func.date(Booking.start_time) <= last_day)) \
                            .filter(Booking.master_id == master_id) \
                            .order_by(Booking.master_id, Booking.start_time) \
                            .all()

            monthly_salary = 0
            monthly_salaries = []

            for row in result:
                user_name           = userdao.get_user_name(row.Booking.user_id)
                org_price           = row.Booking.price_with_task
                status              = row.Booking.cleaning_status
                appointment_index   = row.Booking.appointment_index
                appointment_type    = row.Booking.appointment_type
                additional_task     = row.Booking.additional_task
                start_time          = row.Booking.start_time
                end_time            = row.Booking.estimated_end_time
                cleaning_duration   = row.Booking.cleaning_duration / 6
                charging_price      = row.Booking.charging_price
                is_dirty            = row.Booking.is_dirty
                is_b2b              = row.User.is_b2b

                duration_in_minutes = (end_time - start_time).seconds / 360 # 계산을 단순하게 하기 위해 60 * 60이 아닌 60 * 6으로 나눔. 그뒤 10배 커지는 것을 방지하기 위해 시급에서 10 나눈 값만 곱함
                minutes_for_salary = duration_in_minutes

                #if duration_in_minutes > cleaning_duration: # 30분의 시간이 더 더해지는 경우가 존재. 그 경우, 해당 시간은 임금에 반영 되지 않음
                #    if appointment_index == 1 and (appointment_type == BC.ONE_TIME_A_MONTH or appointment_type == BC.TWO_TIME_A_MONTH or appointment_type == BC.FOUR_TIME_A_MONTH):
                #        minutes_for_salary = duration_in_minutes - 5

                if is_dirty == 1: # 똥집인 경우 2시간 제외해야함
                    minutes_for_salary -= 20

                house_type = row.UserAddress.kind
                house_size = row.UserAddress.size

                if row.Booking.cleaning_status == BC.BOOKING_COMPLETED or \
                    row.Booking.cleaning_status == BC.BOOKING_STARTED or \
                    row.Booking.cleaning_status == BC.BOOKING_UPCOMMING:

                    if is_b2b:
                        monthly_salary += int(minutes_for_salary * (row.Booking.wage_per_hour / 10))
                    else:
                        # 오피스텔 13평 이하, 주택 7평 이하는 시급 14000
                        if appointment_type in BC.REGULAR_CLEANING_DICT:
                            monthly_salary += minutes_for_salary * BC.SALARY_FOR_REGULAR_IN_HOUR
                        else:
                            monthly_salary += minutes_for_salary * BC.SALARY_FOR_ONETIME_IN_HOUR

                        if start_time.weekday() in BC.WEEKEND and start_time >= dt.datetime(2016, 12, 17):
                            monthly_salary += BC.WEEKEND_ADDED_SALARY

                    monthly_salary += bookingdao.get_extra_charge(row.Booking.id)

                elif row.Booking.payment_status == BC.BOOKING_CANCELED_CHARGE or \
                    row.Booking.payment_status == BC.BOOKING_CANCELED_REFUND:
                    monthly_salary += int(charging_price * CANCELED_RATE)

            penalty_amount = masterdao.get_master_penalties(master_id, first_day, last_day)

            monthly_salary = int(monthly_salary * 0.967) # 3.3% 제외
            actual_monthly_salary = monthly_salary - penalty_amount

            monthly_salary = '{:,}'.format(monthly_salary)
            actual_monthly_salary = '{:,}'.format(actual_monthly_salary)
            penalty_amount = '{:,}'.format(penalty_amount)

            from_date_str = dt.datetime.strftime(first_day, '%Y%m%d')
            to_date_str = dt.datetime.strftime(last_day, '%Y%m%d')

            monthly_salaries.append({'date_from' : from_date_str, 'date_to' : to_date_str,
                                    'salary' : monthly_salary, 'penalty_amount' : penalty_amount,
                                    'actual_monthly_salary' : actual_monthly_salary})

            master_row = session.query(Master).filter(Master.id == master_id).one()
            master_name = master_row.name
            master_phone = master_row.phone

            ret['response'] = {'master_name' : master_name, 'master_phone' : master_phone,
                                'monthly_salary' : monthly_salaries}

            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()

            self.write(json.dumps(ret))
