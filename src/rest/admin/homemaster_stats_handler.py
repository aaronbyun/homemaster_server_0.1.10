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
from sqlalchemy import and_, desc, or_, func
from rest.booking import booking_constant as BC
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, Promotion, EventPromotion
from data.encryption import aes_helper as aes
from data.dao.userdao import UserDAO
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict


class HomemasterStatInfoHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        try:
            session = Session()
            userdao = UserDAO()

            SATURDAY = 5
            now = dt.datetime.now()
            offset = (now.weekday() - SATURDAY) % 7

            last_saturday = (now - dt.timedelta(days=offset)).date()
            now = now.date()
            this_friday = last_saturday + dt.timedelta(days=6)

            new_booking_regular_count = session.query(Booking, Promotion) \
                                        .outerjoin(Promotion, Booking.id == Promotion.booking_id) \
                                        .filter(and_(func.date(Booking.start_time) >= last_saturday, func.date(Booking.start_time) <= now)) \
                                        .filter(or_(Booking.appointment_type == BC.ONE_TIME_A_MONTH, Booking.appointment_type == BC.TWO_TIME_A_MONTH, Booking.appointment_type == BC.FOUR_TIME_A_MONTH)) \
                                        .filter(or_(Booking.cleaning_status == BC.BOOKING_STARTED, Booking.cleaning_status == BC.BOOKING_UPCOMMING, Booking.cleaning_status == BC.BOOKING_COMPLETED)) \
                                        .filter(Booking.price != 0) \
                                        .count()

            new_booking_one_count = session.query(Booking, Promotion) \
                                        .outerjoin(Promotion, Booking.id == Promotion.booking_id) \
                                        .filter(and_(func.date(Booking.start_time) >= last_saturday, func.date(Booking.start_time) <= now)) \
                                        .filter(or_(Booking.appointment_type == BC.ONE_TIME, Booking.appointment_type == BC.ONE_TIME_BUT_CONSIDERING)) \
                                        .filter(or_(Booking.cleaning_status == BC.BOOKING_STARTED, Booking.cleaning_status == BC.BOOKING_UPCOMMING, Booking.cleaning_status == BC.BOOKING_COMPLETED)) \
                                        .filter(Booking.price != 0) \
                                        .count()

            total_booking_count = new_booking_regular_count + new_booking_one_count

            expected_list = []
            date_range = []
            date_range.append((last_saturday, now))

            from_date = last_saturday
            to_date = this_friday

            for i in range(4):
                date_range.append((from_date, to_date))

                new_booking_regular_count = session.query(Booking, Promotion) \
                                            .outerjoin(Promotion, Booking.id == Promotion.booking_id) \
                                            .filter(and_(func.date(Booking.start_time) >= from_date, func.date(Booking.start_time) <= to_date)) \
                                            .filter(or_(Booking.appointment_type == BC.ONE_TIME_A_MONTH, Booking.appointment_type == BC.TWO_TIME_A_MONTH, Booking.appointment_type == BC.FOUR_TIME_A_MONTH)) \
                                            .filter(or_(Booking.cleaning_status == BC.BOOKING_STARTED, Booking.cleaning_status == BC.BOOKING_UPCOMMING, Booking.cleaning_status == BC.BOOKING_COMPLETED)) \
                                            .filter(Booking.price != 0) \
                                            .count()

                new_booking_one_count = session.query(Booking, Promotion) \
                                            .outerjoin(Promotion, Booking.id == Promotion.booking_id) \
                                            .filter(and_(func.date(Booking.start_time) >= from_date, func.date(Booking.start_time) <= to_date)) \
                                            .filter(or_(Booking.appointment_type == BC.ONE_TIME, Booking.appointment_type == BC.ONE_TIME_BUT_CONSIDERING)) \
                                            .filter(or_(Booking.cleaning_status == BC.BOOKING_STARTED, Booking.cleaning_status == BC.BOOKING_UPCOMMING, Booking.cleaning_status == BC.BOOKING_COMPLETED)) \
                                            .filter(Booking.price != 0) \
                                            .count()

                from_date = from_date + dt.timedelta(days=7)
                to_date = to_date + dt.timedelta(days=7)

                anticipation_total_booking_count = new_booking_regular_count + new_booking_one_count
                expected_list.append(anticipation_total_booking_count)

            sql = '''select appointment_type, count(appointment_type) as cnt from (select user_id, appointment_type from bookings 
                where (appointment_type = 1 or appointment_type = 2 or appointment_type = 4) and cleaning_status = 0
                group by user_id, appointment_type) t 
                group by appointment_type'''

            result = session.execute(sql).fetchall()

            regular_customer_count = 0
            one_time_a_month_count = 0
            two_time_a_month_count = 0
            four_time_a_month_count = 0

            for row in result:
                item = dict(row)
                regular_customer_count += item['cnt']

                atype = int(item['appointment_type'])
                if atype == BC.ONE_TIME_A_MONTH:
                    one_time_a_month_count = item['cnt']
                elif atype == BC.TWO_TIME_A_MONTH:
                    two_time_a_month_count = item['cnt']
                elif atype == BC.FOUR_TIME_A_MONTH:
                    four_time_a_month_count = item['cnt']


            sql = '''select count(*) as cnt from (
                    select user_id as uid from (
                    select b.*, u.email, c.booking_id, c.reason_id, c.kind 
                        from bookings b
                        join users u 
                        on b.user_id = u.id
                        join cancel_reasons c
                        on b.id = c.booking_id
                        where (b.appointment_type = 1 or b.appointment_type = 2 or b.appointment_type = 4) and c.kind = 1
                        group by user_id) t 
                        where user_id not in (select id as uid from (
                    select u.*, b.cleaning_status, b.appointment_type
                        from users u 
                        join bookings b 
                        on u.id = b.user_id
                        where b.cleaning_status = 0
                        group by u.id) t2))t3'''

            gone_customer = 0
            result = session.execute(sql).fetchall()
            for row in result:
                item = dict(row)
                gone_customer = int(item['cnt'])


            # availability ratio
            sql = '''select sum(available - actual) / 60 as actual, sum(available) / 60 as available from (
                        select master_id, start_time, sum(actual) as actual, available from (
                        select b.master_id, start_time, time_to_sec(timediff(b.estimated_end_time, b.start_time)) / 60 as actual, ifnull(time_to_sec(timediff(s.free_to, s.free_from)) / 60, 600) as available 
                            from bookings b
                            left join master_schedules_by_date s 
                            on b.master_id = s.master_id and date(b.start_time) = s.date
                            where b.cleaning_status > -1 and date(b.start_time) >= :date1 and date(b.start_time) <= :date2
                            and b.price != 0
                            order by master_id, date(start_time))t
                            group by master_id, date(start_time))t
                            where available - actual >= 180'''

            query_param = {'date1' : last_saturday, 'date2' : this_friday}    
            
            result = session.execute(sql, query_param).fetchall()
            item = dict(result[0])

            actual = str(int(item['actual'])) + '시간'
            available = str(int(item['available'])) + '시간'

            ret['response'] = {'cleaning_count' : total_booking_count, 
                                'expected_cleaning_count' : expected_list, 
                                'actual' : actual,
                                'available' : available,
                                'regular_customer' : regular_customer_count, 
                                'one' : one_time_a_month_count, 'two' : two_time_a_month_count, 'four' : four_time_a_month_count, 
                                'gone' : gone_customer}

            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))