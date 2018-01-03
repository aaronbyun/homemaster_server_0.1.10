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
import requests
import datetime as dt
from rest.booking import booking_constant as BC
from data.dao.userdao import UserDAO
from data.dao.bookingdao import BookingDAO
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, Rating, Master, User, UserAddress
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import and_, func, or_
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel


class WeeklyIndicatorHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        ret = {}

        try:
            SATURDAY = 5
            now = dt.datetime.now()
            #now -= dt.timedelta(days=2)
            #now = dt.datetime(2016, 8, 5)
            offset = (now.weekday() - SATURDAY) % 7
            #offset = 6

            last_saturday = (now - dt.timedelta(days=offset)).date()
            now           = now.date()

            print last_saturday, now
            # 신규, 이탈, 평점, 매출, 이익
            income          = self.get_income(last_saturday, now)
            total_salary    = self.get_total_salaries(last_saturday, now)
            regular         = self.get_new_regular(last_saturday, now)
            single          = self.get_new_single(last_saturday, now)
            leave           = self.get_leave(last_saturday, now)
            average_rating  = self.get_average_rating(last_saturday, now)

            surplus = '{:,}'.format(income - total_salary)
            income = '{:,}'.format(income)

            ret['response'] = {'income' : income,
                                'surplus' : surplus,
                                'new_all' : regular + single,
                                'new_regular' : regular,
                                'rating' : average_rating,
                                'leave' : leave,
                                'start_date' : dt.datetime.strftime(last_saturday, '%Y%m%d'),
                                'end_date' : dt.datetime.strftime(now, '%Y%m%d')}
        except Exception, e:
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            self.write(json.dumps(ret))

    def get_new_regular(self, start_date, end_date):
        query = '''select count(*) from bookings
            	where date(booking_time) >= :start_date
                and date(booking_time) <= :end_date
                and (appointment_type = 1 or appointment_type = 2 or appointment_type = 4)
                and appointment_index = 1
                and cleaning_status > -1'''

        query_param = {'start_date' : start_date, 'end_date' : end_date}

        session = Session()
        result = session.execute(query, query_param).fetchall()

        print result[0].items()[0][1]
        return int(result[0].items()[0][1])


    def get_new_single(self, start_date, end_date):
        query = '''select count(*) from bookings
            	where date(booking_time) >= :start_date
                and date(booking_time) <= :end_date
                and (appointment_type = 0 or appointment_type = 3)
                and appointment_index = 1
                and cleaning_status > -1'''

        query_param = {'start_date' : start_date, 'end_date' : end_date}

        session = Session()
        result = session.execute(query, query_param).fetchall()

        print result[0].items()[0][1]
        return int(result[0].items()[0][1])


    def get_leave(self, start_date, end_date):
        query = '''select count(*) as cnt from (
                    select user_id as uid from (
                    select b.*, u.email, c.booking_id, c.reason_id, c.kind
                        from bookings b
                        join users u
                        on b.user_id = u.id
                        join cancel_reasons c
                        on b.id = c.booking_id
                        where (b.appointment_type = 1 or b.appointment_type = 2 or b.appointment_type = 4) and c.kind = 1
                        and date(c.cancel_time) >= :start_date and date(c.cancel_time) <= :end_date
                        group by user_id) t
                        where user_id not in (select id as uid from (
                    select u.*, b.cleaning_status, b.appointment_type
                        from users u
                        join bookings b
                        on u.id = b.user_id
                        where b.cleaning_status = 0
                        group by u.id) t2))t3'''

        query_param = {'start_date' : start_date, 'end_date' : end_date}

        session = Session()
        result = session.execute(query, query_param).fetchall()

        print result[0].items()[0][1]
        return int(result[0].items()[0][1])

    def get_income(self, start_date, end_date):
        query = '''select sum(price_with_task) + sum(charging_price) + sum(ifnull(p.discount_price, 0)) + sum(ifnull(pb.discount_price, 0))
            	from bookings b
                left join promotions p
                on b.id = p.booking_id
                left join event_promotion_bookings pb
                on b.id = pb.booking_id
                join users u
                on b.user_id = u.id
                where date(b.start_time) >= :start_date and  date(b.start_time) <= :end_date
                and u.email not like '%@b2b.com'
                and b.cleaning_status > -1'''

        query_param = {'start_date' : start_date, 'end_date' : end_date}

        session = Session()
        result = session.execute(query, query_param).fetchall()

        print result[0].items()[0][1]
        return int(result[0].items()[0][1])

    def get_total_salaries(self, start_date, end_date):
        FRIDAY = 4
        SATURDAY = 5
        CANCELED_RATE = 0.5

        bookingdao = BookingDAO()
        session = Session()
        result = session.query(Booking, Master, User, UserAddress) \
                        .join(Master, Booking.master_id == Master.id) \
                        .join(User, Booking.user_id == User.id) \
                        .join(UserAddress, and_(Booking.user_id == UserAddress.user_id, Booking.addr_idx == UserAddress.user_addr_index)) \
                        .filter(and_(func.date(Booking.start_time) >= start_date, func.date(Booking.start_time) <= end_date)) \
                        .filter(or_(Booking.cleaning_status == BC.BOOKING_COMPLETED, Booking.cleaning_status == BC.BOOKING_CANCELED)) \
                        .order_by(Booking.master_id, Booking.start_time) \
                        .all()

        weekly_salary = 0
        prev_master_id = None

        for row in result:
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

        session.close()
        return weekly_salary


    # 주간 평점
    def get_average_rating(self, start_date, end_date):
        session = Session()
        result = session.query(Booking, Rating) \
                    .join(Rating, Booking.id == Rating.booking_id) \
                    .filter(and_(func.date(Booking.start_time) >= start_date, func.date(Booking.start_time) <= end_date)) \

        total_rating = 0
        count = 0
        for row in result:
            master_rating = (float(row.Rating.rate_clean) + float(row.Rating.rate_master)) / 2.0
            total_rating += master_rating

            count += 1

        session.close()

        if count != 0:
            return "{0:.2f}".format(total_rating / count)
        else:
            return 0
