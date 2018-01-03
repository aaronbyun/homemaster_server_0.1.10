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
from data.dao.masterdao import MasterDAO
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, Master, UserPaymentRecord, Promotion, MasterPoint, User, UserAddress
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import func, and_, or_
from err.error_handler import print_err_detail, err_dict
from response import Response
from response import add_err_message_to_response
from master_constant import master_fee_rate_dict
from data.encryption import aes_helper as aes
from salary.salary_helper import send_money

class SendSalaryHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        passcode = self.get_argument('passcode', 0) # n weeks before

        ret = {}

        FRIDAY = 4
        SATURDAY = 5
        CANCELED_RATE = 0.5

        try:
            session = Session()
            userdao = UserDAO()
            masterdao = MasterDAO()
            bookingdao = BookingDAO()

            # get last saturday
            now = dt.datetime.now()
            week = 1
            if week != 0:
                offset = ((now.weekday() - FRIDAY) % 7) + (week - 1) * 7
                now -= dt.timedelta(days=offset)

            offset = (now.weekday() - SATURDAY) % 7
            last_saturday = (now - dt.timedelta(days=offset)).date()
            now = now.date()

            result = session.query(Booking, Master, User, UserAddress) \
                            .join(Master, Booking.master_id == Master.id) \
                            .join(User, Booking.user_id == User.id) \
                            .join(UserAddress, and_(Booking.user_id == UserAddress.user_id, Booking.addr_idx == UserAddress.user_addr_index)) \
                            .filter(and_(func.date(Booking.start_time) >= last_saturday, func.date(Booking.start_time) <= now)) \
                            .filter(or_(Booking.cleaning_status == BC.BOOKING_COMPLETED, Booking.cleaning_status == BC.BOOKING_CANCELED)) \
                            .order_by(Booking.master_id, Booking.start_time) \
                            .all()

            weekly_salary = 0

            master_salaries = []

            start_period = last_saturday
            end_period = now

            last_saturday = dt.datetime.strftime(last_saturday, '%Y%m%d')
            now = dt.datetime.strftime(now, '%Y%m%d')

            prev_master_id = None

            for row in result:
                if row.Booking.user_id == '81c2f5c1-7295-489d-8bb0-334121060ae3':
                    continue

                user_name           = userdao.get_user_name(row.Booking.user_id)
                org_price           = row.Booking.price_with_task
                status              = row.Booking.cleaning_status
                appointment_index   = row.Booking.appointment_index
                appointment_type    = row.Booking.appointment_type
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

                extra_charge = 0
                if row.Booking.cleaning_status == BC.BOOKING_COMPLETED:
                    # 오피스텔 13평 이하, 주택 7평 이하는 시급 14000
                    weekly_salary = 0
                    if is_b2b:
                        weekly_salary = int(minutes_for_salary * (row.Booking.wage_per_hour / 10))
                    else:
                        if appointment_type in BC.REGULAR_CLEANING_DICT:
                            weekly_salary = minutes_for_salary * BC.SALARY_FOR_REGULAR_IN_HOUR
                        else:
                            weekly_salary = minutes_for_salary * BC.SALARY_FOR_ONETIME_IN_HOUR

                        if start_time.weekday() in BC.WEEKEND and start_time >= dt.datetime(2016, 12, 17):
                            weekly_salary += BC.WEEKEND_ADDED_SALARY

                    extra_charge = bookingdao.get_extra_charge(row.Booking.id)
                    weekly_salary += extra_charge

                elif row.Booking.payment_status == BC.BOOKING_CANCELED_CHARGE or \
                    row.Booking.payment_status == BC.BOOKING_CANCELED_REFUND:
                    weekly_salary = int(charging_price * CANCELED_RATE)

                if prev_master_id == None or prev_master_id != row.Booking.master_id: # 변함
                    salary = {}
                    salary_detail = []
                    bank_name, bank_code, account_no = masterdao.get_master_account(row.Booking.master_id)

                    salary['weekly_salary'] = 0
                    salary['master_name'] = row.Master.name
                    salary['master_account'] = {'bank_name' : bank_name, 'bank_code' : bank_code, 'account_no' : account_no}
                    salary['master_phone'] = row.Master.phone
                    salary['weekly_salary'] += weekly_salary
                    salary['penalty_amount'] = masterdao.get_master_penalties(row.Booking.master_id, start_period, end_period)

                    master_salaries.append(salary)
                else:
                    salary['weekly_salary'] += weekly_salary


                prev_master_id = row.Master.id

            for ms in master_salaries:
                ms['weekly_salary'] = int(ms['weekly_salary'] * 0.967)
                ms['actual_weekly_salary'] = ms['weekly_salary'] - ms['penalty_amount']

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()

            self.write(json.dumps(ret))
