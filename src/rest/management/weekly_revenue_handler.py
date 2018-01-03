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

class WeeklyRevenueHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")

        ret = {}
        SATURDAY = 5
        CANCELED_RATE = 0.5

        try:
            session = Session()
            userdao = UserDAO()
            bookingdao = BookingDAO()

            # get last saturday
            now = dt.datetime.now()
            offset = (now.weekday() - SATURDAY) % 7

            last_saturday = (now - dt.timedelta(days=offset)).date()
            now = now.date()

            result = session.query(Booking, Master, User, UserAddress) \
                            .join(Master, Booking.master_id == Master.id) \
                            .join(User, Booking.user_id == User.id) \
                            .join(UserAddress, and_(Booking.user_id == UserAddress.user_id, Booking.addr_idx == UserAddress.user_addr_index)) \
                            .filter(and_(func.date(Booking.start_time) >= last_saturday, func.date(Booking.start_time) <= now)) \
                            .filter(not_(User.email.like('%@b2b.com'))) \
                            .order_by(Booking.master_id, Booking.start_time) \
                            .all()

            weekly_salary = 0
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
                is_b2b              = row.User.is_b2b

                duration_in_minutes = (end_time - start_time).seconds / 360 # 계산을 단순하게 하기 위해 60 * 60이 아닌 60 * 6으로 나눔. 그뒤 10배 커지는 것을 방지하기 위해 시급에서 10 나눈 값만 곱함
                minutes_for_salary = duration_in_minutes

                #if duration_in_minutes > cleaning_duration: # 30분의 시간이 더 더해지는 경우가 존재. 그 경우, 해당 시간은 임금에 반영 되지 않음
                #    minutes_for_salary = duration_in_minutes - 5

                house_type = row.UserAddress.kind
                house_size = row.UserAddress.size

                extra_charge = 0
                if row.Booking.cleaning_status == BC.BOOKING_COMPLETED:
                    if is_b2b:
                        weekly_salary += int(minutes_for_salary * (row.Booking.wage_per_hour / 10))
                    else:
                        # 오피스텔 13평 이하, 주택 7평 이하는 시급 14000
                        if appointment_type in BC.REGULAR_CLEANING_DICT:
                            weekly_salary += minutes_for_salary * BC.SALARY_FOR_REGULAR_IN_HOUR
                        else:
                            weekly_salary += minutes_for_salary * BC.SALARY_FOR_ONETIME_IN_HOUR

                        if start_time.weekday() in BC.WEEKEND and start_time >= dt.datetime(2016, 12, 17):
                            weekly_salary += BC.WEEKEND_ADDED_SALARY

                    extra_charge = bookingdao.get_extra_charge(row.Booking.id)
                    weekly_salary += extra_charge

                elif row.Booking.payment_status == BC.BOOKING_CANCELED_CHARGE or \
                    row.Booking.payment_status == BC.BOOKING_CANCELED_REFUND:
                    weekly_salary += int(charging_price * CANCELED_RATE)

            ret['response'] = {'weekly_salary' : weekly_salary, 'revenue' : 100}
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()

            self.write(json.dumps(ret))
