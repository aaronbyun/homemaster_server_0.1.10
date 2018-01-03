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
from data.model.data_model import Booking, Master, UserPaymentRecord, MasterPoint, User, UserAddress
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import func, and_, desc, or_
from sqlalchemy.sql.expression import text
from err.error_handler import print_err_detail, err_dict
from response import Response
from response import add_err_message_to_response
from master_constant import master_fee_rate_dict

class NewMasterSalaryHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        master_id = self.get_argument('master_id', '')

        ret = {}

        # weekly
        SATURDAY = 5
        CANCELED_RATE = 0.5

        try:
            session = Session()
            # get last saturday
            userdao = UserDAO()
            masterdao = MasterDAO()
            bookingdao = BookingDAO()

            now = dt.datetime.now()
            offset = (now.weekday() - SATURDAY) % 7

            last_saturday = (now - dt.timedelta(days=offset)).date()
            now = now.date()

            date_range = []
            date_range.append((last_saturday, now))

            from_date = last_saturday - dt.timedelta(days=7)
            to_date = last_saturday - dt.timedelta(days=1)

            for i in range(11):
                date_range.append((from_date, to_date))

                from_date = from_date - dt.timedelta(days=7)
                to_date = to_date - dt.timedelta(days=7)

            weekly_salaries = []

            start_time = dt.datetime.now()

            for dr in date_range:
                from_date = dr[0]
                to_date = dr[1]

                result = session.query(Booking, Master, User, UserAddress) \
                                .join(Master, Booking.master_id == Master.id) \
                                .join(User, Booking.user_id == User.id) \
                                .join(UserAddress, and_(Booking.user_id == UserAddress.user_id, Booking.addr_idx == UserAddress.user_addr_index)) \
                                .filter(and_(func.date(Booking.start_time) >= from_date, func.date(Booking.start_time) <= to_date)) \
                                .filter(Booking.master_id == master_id) \
                                .filter(or_(Booking.cleaning_status == BC.BOOKING_COMPLETED, \
                                and_(Booking.cleaning_status == BC.BOOKING_CANCELED, \
                                or_(Booking.payment_status == BC.BOOKING_CANCELED_REFUND, \
                                Booking.payment_status == BC.BOOKING_CANCELED_CHARGE)))) \
                                .order_by(Booking.master_id, Booking.start_time) \
                                .all()

                weekly_salary = 0

                for row in result:
                    if row.Booking.user_id == '81c2f5c1-7295-489d-8bb0-334121060ae3':
                        continue

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

                    if is_dirty == 1:
                        minutes_for_salary -= 20

                    house_type = row.UserAddress.kind
                    house_size = row.UserAddress.size

                    if row.Booking.cleaning_status == BC.BOOKING_COMPLETED:
                        if is_b2b:
                            weekly_salary += int(minutes_for_salary * (row.Booking.wage_per_hour / 10))
                        else:
                            # 오피스텔 13평 이하, 주택 7평 이하는 시급 14000
                            if start_time >= dt.datetime(2017, 1, 1):
                                weekly_salary += minutes_for_salary * BC.SALARY_FOR_ONETIME_IN_HOUR
                            else:
                                if appointment_type in BC.REGULAR_CLEANING_DICT:
                                    weekly_salary += minutes_for_salary * BC.SALARY_FOR_REGULAR_IN_HOUR
                                else:
                                    weekly_salary += minutes_for_salary * BC.SALARY_FOR_ONETIME_IN_HOUR

                            if start_time.weekday() in BC.WEEKEND and start_time >= dt.datetime(2016, 12, 17):
                                weekly_salary += BC.WEEKEND_ADDED_SALARY

                        weekly_salary += bookingdao.get_extra_charge(row.Booking.id)

                    elif row.Booking.payment_status == BC.BOOKING_CANCELED_CHARGE or \
                        row.Booking.payment_status == BC.BOOKING_CANCELED_REFUND:
                        weekly_salary += int(charging_price * CANCELED_RATE)

                penalty_amount = 0 #masterdao.get_master_penalties(master_id, from_date, to_date)

                weekly_salary = int(weekly_salary)
                if start_time >= dt.datetime(2017, 1, 1):
                    weekly_salary = int(weekly_salary)
                else:
                    weekly_salary = int(weekly_salary * 0.967)

                actual_weekly_salary = weekly_salary - penalty_amount

                weekly_salary = '{:,}'.format(weekly_salary)
                actual_weekly_salary = '{:,}'.format(actual_weekly_salary)
                penalty_amount = '{:,}'.format(penalty_amount)

                from_date_str = dt.datetime.strftime(from_date, '%Y%m%d')
                to_date_str = dt.datetime.strftime(to_date, '%Y%m%d')

                weekly_salaries.append({'date_from' : from_date_str, 'date_to' : to_date_str,
                                        'salary' : weekly_salary, 'penalty_amount' : penalty_amount,
                                        'actual_weekly_salary' : actual_weekly_salary})

            # montly
            '''monthly_salaries = []

            date_range = []

            from_date = dt.date(now.year, now.month, 1)
            to_date = now

            date_range.append((from_date, to_date))

            for i in range(11):
                to_date = from_date - dt.timedelta(days=1)
                from_date = dt.date(to_date.year, to_date.month, 1)

                date_range.append((from_date, to_date))

            for dr in date_range:
                from_date = dr[0]
                to_date = dr[1]

                result = session.query(Booking, Master, User, UserAddress) \
                                .join(Master, Booking.master_id == Master.id) \
                                .join(User, Booking.user_id == User.id) \
                                .join(UserAddress, and_(Booking.user_id == UserAddress.user_id, Booking.addr_idx == UserAddress.user_addr_index)) \
                                .filter(and_(func.date(Booking.start_time) >= from_date, func.date(Booking.start_time) <= to_date)) \
                                .filter(Booking.master_id == master_id) \
                                .order_by(Booking.master_id, Booking.start_time) \
                                .all()

                monthly_salary = 0

                for row in result:
                    user_name           = userdao.get_user_name(row.Booking.user_id)
                    org_price           = row.Booking.price_with_task
                    status              = row.Booking.cleaning_status
                    appointment_index   = row.Booking.appointment_index
                    appointment_type    = row.Booking.appointment_type
                    start_time          = row.Booking.start_time
                    end_time            = row.Booking.estimated_end_time
                    cleaning_duration   = row.Booking.cleaning_duration / 6
                    charging_price      = row.Booking.charging_price

                    duration_in_minutes = (end_time - start_time).seconds / 360 # 계산을 단순하게 하기 위해 60 * 60이 아닌 60 * 6으로 나눔. 그뒤 10배 커지는 것을 방지하기 위해 시급에서 10 나눈 값만 곱함
                    minutes_for_salary = duration_in_minutes

                    if duration_in_minutes > cleaning_duration: # 30분의 시간이 더 더해지는 경우가 존재. 그 경우, 해당 시간은 임금에 반영 되지 않음
                        minutes_for_salary = duration_in_minutes - 5

                    house_type = row.UserAddress.kind
                    house_size = row.UserAddress.size

                    if row.Booking.cleaning_status == BC.BOOKING_COMPLETED:
                        # 오피스텔 13평 이하, 주택 7평 이하는 시급 14000
                        if ((house_type == 0 and house_size <= 12) or (house_type == 1 and house_size <= 7)):
                            monthly_salary += minutes_for_salary * BC.SALARY_FOR_SMALL_IN_HOUR
                        else:
                            monthly_salary += minutes_for_salary * BC.SALARY_FOR_NORMAL_IN_HOUR

                        monthly_salary += bookingdao.get_extra_charge(row.Booking.id)

                    elif row.Booking.payment_status == BC.BOOKING_CANCELED_CHARGE or \
                        row.Booking.payment_status == BC.BOOKING_CANCELED_REFUND:
                        monthly_salary += int(charging_price * CANCELED_RATE)

                monthly_salary = int(monthly_salary)
                monthly_salary = '{:,}'.format(monthly_salary)

                from_date_str = dt.datetime.strftime(from_date, '%Y%m%d')
                to_date_str = dt.datetime.strftime(to_date, '%Y%m%d')

                monthly_salaries.append({'date_from' : from_date_str, 'date_to' : to_date_str, 'salary' : monthly_salary})

            # total
            total_salary = 0
            result = session.query(Booking, Master, User, UserAddress) \
                            .join(Master, Booking.master_id == Master.id) \
                            .join(User, Booking.user_id == User.id) \
                            .join(UserAddress, and_(Booking.user_id == UserAddress.user_id, Booking.addr_idx == UserAddress.user_addr_index)) \
                            .filter(Booking.master_id == master_id) \
                            .order_by(Booking.master_id, Booking.start_time) \
                            .all()

            for row in result:
                user_name           = userdao.get_user_name(row.Booking.user_id)
                org_price           = row.Booking.price_with_task
                status              = row.Booking.cleaning_status
                appointment_index   = row.Booking.appointment_index
                appointment_type    = row.Booking.appointment_type
                start_time          = row.Booking.start_time
                end_time            = row.Booking.estimated_end_time
                cleaning_duration   = row.Booking.cleaning_duration / 6
                charging_price      = row.Booking.charging_price

                duration_in_minutes = (end_time - start_time).seconds / 360 # 계산을 단순하게 하기 위해 60 * 60이 아닌 60 * 6으로 나눔. 그뒤 10배 커지는 것을 방지하기 위해 시급에서 10 나눈 값만 곱함
                minutes_for_salary = duration_in_minutes

                if duration_in_minutes > cleaning_duration: # 30분의 시간이 더 더해지는 경우가 존재. 그 경우, 해당 시간은 임금에 반영 되지 않음
                    minutes_for_salary = duration_in_minutes - 5

                house_type = row.UserAddress.kind
                house_size = row.UserAddress.size

                if row.Booking.cleaning_status == BC.BOOKING_COMPLETED:
                    # 오피스텔 13평 이하, 주택 7평 이하는 시급 14000
                    if ((house_type == 0 and house_size <= 12) or (house_type == 1 and house_size <= 7)):
                        total_salary += minutes_for_salary * BC.SALARY_FOR_SMALL_IN_HOUR
                    else:
                        total_salary += minutes_for_salary * BC.SALARY_FOR_NORMAL_IN_HOUR

                    total_salary += bookingdao.get_extra_charge(row.Booking.id)

                elif row.Booking.payment_status == BC.BOOKING_CANCELED_CHARGE or \
                    row.Booking.payment_status == BC.BOOKING_CANCELED_REFUND:
                    total_salary += int(charging_price * CANCELED_RATE)

            total_salary = int(total_salary)
            total_salary = '{:,}'.format(total_salary)'''

            # get master point
            #master_point = 0
            #point_row = session.query(func.sum(MasterPoint.point)).filter(MasterPoint.master_id == master_id).all()
            #master_point = int(point_row[0][0])

            master_row = session.query(Master).filter(Master.id == master_id).one()
            master_name = master_row.name
            master_phone = master_row.phone

            ret['response'] = {'master_name' : master_name, 'master_phone' : master_phone,
                                'weekly_salary' : weekly_salaries, 'total_salary' : 0,
                                'monthly_salary' : []}
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()

            self.write(json.dumps(ret))
