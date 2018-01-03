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
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, Master, UserPaymentRecord, Promotion, MasterPoint, User, EventPromotionBooking, UserPaymentRecordForIOS
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import func, and_, desc
from sqlalchemy.sql.expression import text
from err.error_handler import print_err_detail, err_dict
from response import Response
from response import add_err_message_to_response
from master_constant import master_fee_rate_dict

class MasterSalaryPeriodHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        master_id = self.get_argument('master_id', '')

        ret = {}

        # weekly
        SATURDAY = 5
        CANCELED_RATE = 0.7

        try:
            session = Session()
                        # get last saturday
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

            for dr in date_range:
                from_date = dr[0]
                to_date = dr[1]

                result = session.query(Booking, UserPaymentRecord, UserPaymentRecordForIOS, EventPromotionBooking, Promotion, Master, User) \
                                .outerjoin(UserPaymentRecord, Booking.id == UserPaymentRecord.booking_id) \
                                .outerjoin(UserPaymentRecordForIOS, Booking.id == UserPaymentRecordForIOS.booking_id) \
                                .outerjoin(Promotion, Booking.id == Promotion.booking_id) \
                                .outerjoin(EventPromotionBooking, Booking.id == EventPromotionBooking.booking_id) \
                                .join(Master, Booking.master_id == Master.id) \
                                .join(User, Booking.user_id == User.id) \
                                .filter(Booking.master_id == master_id) \
                                .filter(and_(func.date(Booking.start_time) >= dt.date(2015, 11, 21), func.date(Booking.start_time) <= dt.date(2015, 11, 27))) \
                                .all()

                weekly_salary = 0

                for row in result:
                    appointment_type = row.Booking.appointment_type
                    fee_rate = master_fee_rate_dict[appointment_type]

                    if row.Booking.cleaning_status == BC.BOOKING_COMPLETED:
                        canceled_amount = 0 # 취소가 되었다면 그만큼 공제
                        if row.UserPaymentRecord != None:
                            canceled_amount = row.UserPaymentRecord.canceled_amount

                        discount_amount = 0 # 할일코드가 발급된 거라면, 그만큼 금액 추가
                        if row.Promotion != None:
                            discount_amount = row.Promotion.discount_price

                        if row.EventPromotionBooking != None:
                            discount_amount = row.EventPromotionBooking.discount_price

                        if row.UserPaymentRecord == None:
                            org_salary = row.Booking.price_with_task 
                        else:
                            org_salary = row.UserPaymentRecord.price
                            if row.UserPaymentRecord.status == 'CHARGED':
                                discount_amount = 0

                        charging_price = row.Booking.charging_price
                        manual_charging_price = 0
                        if row.UserPaymentRecordForIOS != None:
                            manual_charging_price += row.UserPaymentRecordForIOS.amount

                        weekly_salary += (org_salary + charging_price + manual_charging_price - canceled_amount + discount_amount) * fee_rate
                    elif row.Booking.payment_status == BC.BOOKING_CANCELED_CHARGE:
                        if row.User.devicetype == 'android':
                            weekly_salary += row.Booking.charging_price * fee_rate * CANCELED_RATE
                    elif row.Booking.payment_status == BC.BOOKING_CANCELED_REFUND:
                        if row.User.devicetype == 'android':
                            weekly_salary += row.Booking.charging_price * fee_rate * CANCELED_RATE


                weekly_salary = int(weekly_salary)
                weekly_salary = '{:,}'.format(weekly_salary)

                from_date_str = dt.datetime.strftime(from_date, '%Y%m%d')
                to_date_str = dt.datetime.strftime(to_date, '%Y%m%d')

                weekly_salaries.append({'date_from' : from_date_str, 'date_to' : to_date_str, 'salary' : weekly_salary})

            # montly
            monthly_salaries = []

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

                result = session.query(Booking, UserPaymentRecord, UserPaymentRecordForIOS, EventPromotionBooking, Promotion, Master) \
                                .outerjoin(UserPaymentRecord, Booking.id == UserPaymentRecord.booking_id) \
                                .outerjoin(UserPaymentRecordForIOS, Booking.id == UserPaymentRecordForIOS.booking_id) \
                                .outerjoin(Promotion, Booking.id == Promotion.booking_id) \
                                .outerjoin(EventPromotionBooking, Booking.id == EventPromotionBooking.booking_id) \
                                .join(Master, Booking.master_id == Master.id) \
                                .filter(Booking.master_id == master_id) \
                                .filter(and_(func.date(Booking.start_time) >= from_date, func.date(Booking.start_time) <= to_date)) \
                                .all()

                monthly_salary = 0

                for row in result:
                    appointment_type = row.Booking.appointment_type
                    fee_rate = master_fee_rate_dict[appointment_type]

                    if row.Booking.cleaning_status == BC.BOOKING_COMPLETED:
                        canceled_amount = 0 # 취소가 되었다면 그만큼 공제
                        if row.UserPaymentRecord != None:
                            canceled_amount = row.UserPaymentRecord.canceled_amount

                        discount_amount = 0 # 할일코드가 발급된 거라면, 그만큼 금액 추가
                        if row.Promotion != None:
                            discount_amount = row.Promotion.discount_price

                        if row.EventPromotionBooking != None:
                            discount_amount = row.EventPromotionBooking.discount_price

                        if row.UserPaymentRecord == None:
                            org_salary = row.Booking.price_with_task 
                        else:
                            org_salary = row.UserPaymentRecord.price
                            if row.UserPaymentRecord.status == 'CHARGED':
                                discount_amount = 0

                        charging_price = row.Booking.charging_price
                        manual_charging_price = 0
                        if row.UserPaymentRecordForIOS != None:
                            manual_charging_price += row.UserPaymentRecordForIOS.amount

                        monthly_salary += (org_salary + charging_price + manual_charging_price - canceled_amount + discount_amount) * fee_rate
                    elif row.Booking.payment_status == BC.BOOKING_CANCELED_CHARGE:
                        monthly_salary += row.Booking.charging_price * fee_rate * CANCELED_RATE
                    elif row.Booking.payment_status == BC.BOOKING_CANCELED_REFUND:
                        monthly_salary += row.Booking.charging_price * fee_rate * CANCELED_RATE


                monthly_salary = int(monthly_salary)
                monthly_salary = '{:,}'.format(monthly_salary)

                from_date_str = dt.datetime.strftime(from_date, '%Y%m%d')
                to_date_str = dt.datetime.strftime(to_date, '%Y%m%d')

                monthly_salaries.append({'date_from' : from_date_str, 'date_to' : to_date_str, 'salary' : monthly_salary})

            # total
            total_salary = 0
            result = session.query(Booking, UserPaymentRecord, UserPaymentRecordForIOS, EventPromotionBooking, Promotion, Master) \
                                .outerjoin(UserPaymentRecord, Booking.id == UserPaymentRecord.booking_id) \
                                .outerjoin(UserPaymentRecordForIOS, Booking.id == UserPaymentRecordForIOS.booking_id) \
                                .outerjoin(Promotion, Booking.id == Promotion.booking_id) \
                                .outerjoin(EventPromotionBooking, Booking.id == EventPromotionBooking.booking_id) \
                                .join(Master, Booking.master_id == Master.id) \
                                .filter(Booking.master_id == master_id) \
                                .all()

            for row in result:
                appointment_type = row.Booking.appointment_type
                fee_rate = master_fee_rate_dict[appointment_type]

                if row.Booking.cleaning_status == BC.BOOKING_COMPLETED:
                    canceled_amount = 0 # 취소가 되었다면 그만큼 공제
                    if row.UserPaymentRecord != None:
                        canceled_amount = row.UserPaymentRecord.canceled_amount

                    discount_amount = 0 # 할일코드가 발급된 거라면, 그만큼 금액 추가
                    if row.Promotion != None:
                        discount_amount = row.Promotion.discount_price

                    if row.EventPromotionBooking != None:
                            discount_amount = row.EventPromotionBooking.discount_price

                    if row.UserPaymentRecord == None:
                        org_salary = row.Booking.price_with_task 
                    else:
                        org_salary = row.UserPaymentRecord.price
                        if row.UserPaymentRecord.status == 'CHARGED':
                            discount_amount = 0

                    charging_price = row.Booking.charging_price
                    manual_charging_price = 0
                    if row.UserPaymentRecordForIOS != None:
                        manual_charging_price += row.UserPaymentRecordForIOS.amount

                    total_salary += (org_salary + charging_price + manual_charging_price - canceled_amount + discount_amount) * fee_rate
                elif row.Booking.payment_status == BC.BOOKING_CANCELED_CHARGE:
                    total_salary += row.Booking.charging_price * fee_rate * CANCELED_RATE
                elif row.Booking.payment_status == BC.BOOKING_CANCELED_REFUND:
                    total_salary += row.Booking.charging_price * fee_rate * CANCELED_RATE

            total_salary = int(total_salary)
            total_salary = '{:,}'.format(total_salary)

            # get master point
            #master_point = 0
            #point_row = session.query(func.sum(MasterPoint.point)).filter(MasterPoint.master_id == master_id).all()
            #master_point = int(point_row[0][0])

            master_row = session.query(Master).filter(Master.id == master_id).one()
            master_name = master_row.name
            master_phone = master_row.phone

            ret['response'] = {'master_name' : master_name, 'master_phone' : master_phone, 'weekly_salary' : weekly_salaries, 'total_salary' : total_salary, 'monthly_salary' : monthly_salaries}
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()

            self.write(json.dumps(ret))         