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
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, Master, UserPaymentRecord, Promotion, MasterPoint, User, EventPromotionBooking, UserPaymentRecordForIOS
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import func, and_
from err.error_handler import print_err_detail, err_dict
from response import Response
from response import add_err_message_to_response
from master_constant import master_fee_rate_dict
from data.encryption import aes_helper as aes

class AllWeeklySalaryHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        SATURDAY = 5
        CANCELED_RATE = 0.7

        try:
            session = Session()
            userdao = UserDAO()

            # get last saturday
            now = dt.datetime.now()
            now -= dt.timedelta(days=3)
            offset = (now.weekday() - SATURDAY) % 7

            last_saturday = (now - dt.timedelta(days=offset)).date()
            now = now.date()

            result = session.query(Booking, UserPaymentRecord, UserPaymentRecordForIOS, EventPromotionBooking, Promotion, Master, User) \
                            .outerjoin(UserPaymentRecord, Booking.id == UserPaymentRecord.booking_id) \
                            .outerjoin(UserPaymentRecordForIOS, Booking.id == UserPaymentRecordForIOS.booking_id) \
                            .outerjoin(Promotion, Booking.id == Promotion.booking_id) \
                            .outerjoin(EventPromotionBooking, Booking.id == EventPromotionBooking.booking_id) \
                            .join(Master, Booking.master_id == Master.id) \
                            .join(User, Booking.user_id == User.id) \
                            .filter(and_(func.date(Booking.start_time) >= last_saturday, func.date(Booking.start_time) <= now)) \
                            .order_by(Booking.master_id, Booking.start_time) \
                            .all()

            weekly_salary = 0

            master_salaries = []

            last_saturday = dt.datetime.strftime(last_saturday, '%Y%m%d')
            now = dt.datetime.strftime(now, '%Y%m%d')

            prev_master_id = None

            for row in result:
                appointment_type = row.Booking.appointment_type
                fee_rate = master_fee_rate_dict[appointment_type]

                user_name = userdao.get_user_name(row.Booking.user_id)

                org_salary = 0
                charging_price = 0
                weekly_salary = 0
                status = 0

                canceled_amount = 0 # 관리자 재량으로 취소한 금액이 있다면
                discount_amount = 0 # 할일코드가 발급된 거라면, 그만큼 금액 추가

                if row.Booking.cleaning_status == BC.BOOKING_COMPLETED:
                    if row.UserPaymentRecord != None:
                        canceled_amount = row.UserPaymentRecord.canceled_amount

                    if row.Promotion != None:
                        discount_amount = row.Promotion.discount_price
                        if discount_amount <= 100:
                            discount_amount = row.Promotion.service_price

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

                    # 2016. 03. 08 lily park 요청으로 canceled_amount 막음
                    weekly_salary = (org_salary + charging_price + manual_charging_price - canceled_amount + discount_amount) * fee_rate
                    #weekly_salary = (org_salary + charging_price + manual_charging_price + discount_amount) * fee_rate
                    status = BC.BOOKING_COMPLETED
                    start_time = row.Booking.start_time

                elif row.Booking.payment_status == BC.BOOKING_CANCELED_CHARGE:
                    if row.UserPaymentRecord != None:
                        canceled_amount = row.UserPaymentRecord.canceled_amount

                    org_salary = row.Booking.price_with_task
                    charging_price = row.Booking.charging_price

                    if row.User.devicetype == 'android':
                        weekly_salary = charging_price * fee_rate * CANCELED_RATE
                    status = BC.BOOKING_CANCELED_CHARGE
                    start_time = row.Booking.start_time

                elif row.Booking.payment_status == BC.BOOKING_CANCELED_REFUND:
                    if row.UserPaymentRecord != None:
                        canceled_amount = row.UserPaymentRecord.canceled_amount

                    org_salary = row.Booking.price_with_task
                    charging_price = row.Booking.charging_price
                    print row.Booking.id, row.Booking.master_id, charging_price
                    if row.User.devicetype == 'android':
                        weekly_salary = charging_price * fee_rate * CANCELED_RATE
                    status = BC.BOOKING_CANCELED_REFUND
                    start_time = row.Booking.start_time

                if prev_master_id == None or prev_master_id != row.Booking.master_id: # 변함
                    salary = {}
                    salary_detail = []
                    salary['weekly_salary'] = 0
                    salary['master_name'] = row.Master.name
                    salary['master_phone'] = row.Master.phone
                    salary['weekly_salary'] += int(weekly_salary)

                    if int(weekly_salary) > 0:
                        salary_detail.append({'org_price' : org_salary, 'charging_price' : charging_price, 'canceled_amount' : canceled_amount, 'discount_amount' : discount_amount, 'salary' : int(weekly_salary), 'status' : status, 'start_time' : dt.datetime.strftime(start_time, '%Y-%m-%d %H:%M'), 'user_name' : user_name, 'fee_rate' : fee_rate, 'cancel_fee_rate' : float(fee_rate * CANCELED_RATE)})

                    salary['salary_detail'] = salary_detail

                    master_salaries.append(salary)
                else:
                    salary['weekly_salary'] += int(weekly_salary)
                    if int(weekly_salary) > 0:
                        salary['salary_detail'].append({'org_price' : org_salary, 'charging_price' : charging_price, 'canceled_amount' : canceled_amount, 'discount_amount' : discount_amount, 'salary' : int(weekly_salary), 'status' : status, 'start_time' : dt.datetime.strftime(start_time, '%Y-%m-%d %H:%M'), 'user_name' : user_name, 'fee_rate' : fee_rate, 'cancel_fee_rate' : float(fee_rate * CANCELED_RATE)})

                prev_master_id = row.Master.id

            salary_sum = 0
            for ms in master_salaries:
                salary_sum += ms['weekly_salary']
                ms['weekly_salary'] = '{:,}'.format(ms['weekly_salary'])

            print salary_sum

            ret['response'] = {'date_from' : last_saturday, 'date_to' : now, 'master_salaries' : master_salaries}
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()

            self.write(json.dumps(ret))
