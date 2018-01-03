#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import json
import tornado.ioloop
import tornado.web
import datetime as dt
from hashids import Hashids
from data.dao.userdao import UserDAO
from sqlalchemy import func, Date, cast, or_, and_, desc
from rest.booking import booking_constant as BC
from data.session.mysql_session import engine, Session
from err.error_handler import print_err_detail, err_dict
from data.model.data_model import Booking, User, CancelReason
from err.error_handler import print_err_detail, err_dict
from payment.payment_helper import request_payment, cancel_payment
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from data.mixpanel.mixpanel_helper import get_mixpanel

# charge the user right before start clearning
# add upcoming appointment to database

# 30분 단위로 bookings table에서 해당 날짜의 upcoming table을 찾아서 과금 및 상태를  paid로 변경
# 1회 고객은 예약과 동시에 과금되기 때문에 필요 없다. 정기 예약의 경우에는 다음 일정 추가

class BookingPaymentJob(object):
    def __init__(self):
        pass

    def get_next_appointment_date(self, request_id, appointment_type):
        start_time = ''
        estimated_end_time = ''

        try:
            session = Session()

            row = session.query(func.max(Booking.org_start_time), Booking.cleaning_duration) \
                    .filter(Booking.request_id == request_id) \
                    .group_by(Booking.request_id) \
                    .one()

            start_time = row[0]
            estimated_end_time = start_time + dt.timedelta(minutes = row[1])


            start_time += dt.timedelta(days = BC.DAYS_IN_A_WEEK * (4 / appointment_type))
            estimated_end_time += dt.timedelta(days = BC.DAYS_IN_A_WEEK * (4 / appointment_type))

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()
            return start_time, estimated_end_time

    def get_last_laundry_all(self, request_id):
        laundry_apply_all = 0
        try:
            session = Session()

            row = session.query(Booking) \
                    .filter(Booking.request_id == request_id) \
                    .filter(Booking.cleaning_status == BC.BOOKING_UPCOMMING) \
                    .order_by(desc(Booking.appointment_index)) \
                    .first()

            laundry_apply_all = row.laundry_apply_all

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()
            return laundry_apply_all


    def get_next_appointment_index(self, request_id, status, appointment_type):
        next_index = 0

        try:
            session = Session()

            row = session.query(func.max(Booking.appointment_index)) \
                    .filter(Booking.request_id == request_id) \
                    .filter(or_(Booking.cleaning_status == BC.BOOKING_UPCOMMING, Booking.cleaning_status == BC.BOOKING_STARTED, Booking.cleaning_status == BC.BOOKING_COMPLETED)) \
                    .group_by(Booking.request_id) \
                    .one()

            next_index = row[0] + 1

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()
            return next_index


    def get_org_master(self, request_id):
        master_id = None
        try:
            session = Session()

            row = session.query(Booking.master_id) \
                    .filter(Booking.request_id == request_id) \
                    .filter(Booking.is_master_changed == 0) \
                    .filter(Booking.cleaning_status > -1) \
                    .first()

            if row != None:
                master_id = row[0]

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()
            return master_id


    def is_cancelled_all(self, booking_id):
        canceled_all = True
        try:
            session = Session()

            current_book_start_time = session.query(Booking) \
                                            .filter(Booking.id == booking_id) \
                                            .one() \
                                            .start_time

            stmt = session.query(Booking.request_id).filter(Booking.id == booking_id).subquery()
            booking_group = session.query(Booking) \
                                    .filter(Booking.request_id == stmt) \
                                    .filter(Booking.start_time > current_book_start_time) \
                                    .order_by(Booking.start_time) \
                                    .all()

            for booking in booking_group:
                if not booking.cleaning_status == BC.BOOKING_CANCELED:
                    canceled_all = False
                    break

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()
            return canceled_all


    def add_new_appointment(self, request_id, master_id, user_id, appointment_type, appointment_index,
                                  booking_time, start_time, estimated_end_time, cleaning_duration, additional_task, price, price_with_task,
                                  card_idx, addr_idx, message, trash_location, enterhome, enterbuilding, routing_method, havetools,
                                  havepet, laundry_apply_all, is_dirty, master_gender, wage_per_hour, source, user_type):
        try:
            session = Session()
            now = dt.datetime.strftime(dt.datetime.now(), '%Y%m%d%H%M%S')
            hashids            = Hashids(min_length = 16, salt = user_id + now)
            booking_id         = hashids.encode(int(dt.datetime.strftime(start_time, '%Y%m%d%H%M')))
            dow                = start_time.date().weekday()

            booking = Booking(id = booking_id,
                              request_id = request_id,
                              user_id = user_id,
                              master_id = master_id,
                              appointment_type = appointment_type,
                              appointment_index = appointment_index,
                              dow = dow,
                              booking_time = booking_time,
                              org_start_time = start_time,
                              start_time = start_time,
                              estimated_end_time = estimated_end_time,
                              end_time = estimated_end_time, # update after homemaster finish their job
                              cleaning_duration = cleaning_duration,
                              additional_task = additional_task,
                              price = price,
                              price_with_task = price_with_task,
                              charging_price = 0,
                              card_idx = card_idx,
                              addr_idx = addr_idx,
                              message = message,
                              trash_location = trash_location,
                              enterhome = enterhome,
                              enterbuilding = enterbuilding,
                              routing_method = routing_method,
                              havetools = havetools,
                              havepet = havepet,
                              laundry_apply_all = laundry_apply_all,
                              is_dirty = is_dirty,
                              master_gender = master_gender,
                              source = source,
                              user_type = user_type,
                              wage_per_hour = wage_per_hour,
                              status = BC.BOOKING_UPCOMMING,
                              cleaning_status = BC.BOOKING_UPCOMMING,
                              payment_status = BC.BOOKING_UNPAID_YET)

            session.add(booking)
            session.commit()

            print booking_id, 'was successfully added for user :', user_id, 'by cron job at', dt.datetime.now()
        except Exception, e:
            session.rollback()
            print_err_detail(e)
            raise Exception(e)

        finally:
            session.close()


    def charge(self):
        try:
            print '-' * 40
            print 'charge started'
            current_time = dt.datetime.now()

            print current_time

            hour = current_time.hour
            minute = 30 if current_time.minute >= 30 else 0

            cron_time = current_time.replace(hour=hour, minute=minute, second = 0, microsecond = 0)
            print cron_time
            print '-' * 40

            userdao = UserDAO()

            session = Session()
            result = session.query(Booking) \
                                .filter(or_(Booking.cleaning_status == BC.BOOKING_UPCOMMING, Booking.cleaning_status == BC.BOOKING_STARTED)) \
                                .filter(Booking.payment_status == BC.BOOKING_UNPAID_YET) \
                                .filter(func.date(Booking.start_time) == cron_time.date()) \
                                .filter(func.HOUR(Booking.start_time) == cron_time.time().hour) \
                                .filter(func.MINUTE(Booking.start_time) == cron_time.time().minute) \
                                .all()

            for row in result:
                try:
                    # payment
                    booking_id = row.id
                    user_id = row.user_id
                    price = int(row.price_with_task)
                    user_name = userdao.get_user_name(user_id)

                    devicetype = userdao.get_user_device_type(user_id)
                    if devicetype == 'None': # 안드로이드 사용자만 자동 과금한다
                        continue

                    print booking_id, user_id, price, user_name, 'tried to pay'

                    ret_code, msg = request_payment(user_id, user_name, booking_id, price, row.appointment_type) # 자동 결제 성공
                    if ret_code:
                        # paid 로 상태 변경이 필요함
                        card_idx = userdao.get_user_default_card_index(user_id)

                        tid = msg
                        row.card_idx = card_idx
                        row.tid = tid
                        row.payment_status = BC.BOOKING_PAID
                        #row.cleaning_status = BC.BOOKING_UPCOMMING
                        row.status = BC.BOOKING_PAID
                        print tid, 'success'
                    else: # 자동 결제 실패
                        row.payment_status = BC.BOOKING_PAYMENT_FAILED
                        #row.cleaning_status = BC.BOOKING_UPCOMMING
                        row.status == BC.BOOKING_PAYMENT_FAILED
                        print msg, 'failed'

                    session.commit()

                except Exception, e:
                    session.rollback()
                    print_err_detail(e)
                    continue

        except Exception, e:
            session.rollback()
            print_err_detail(e)

        finally:
            session.close()


    def add_upcoming(self):
        try:
            print '-' * 40
            print 'charge and add upcoming appointment started'
            current_time = dt.datetime.now()

            print current_time

            hour = current_time.hour
            minute = 30 if current_time.minute >= 30 else 0

            cron_time = current_time.replace(hour=hour, minute=minute, second = 0, microsecond = 0)
            print cron_time
            print '-' * 40

            userdao = UserDAO()
            session = Session()
            result = session.query(Booking) \
                                .filter(or_(Booking.appointment_type == BC.ONE_TIME_A_MONTH, Booking.appointment_type == BC.TWO_TIME_A_MONTH, Booking.appointment_type == BC.FOUR_TIME_A_MONTH)) \
                                .filter(func.date(Booking.start_time) == cron_time.date()) \
                                .filter(func.HOUR(Booking.start_time) == cron_time.time().hour) \
                                .filter(func.MINUTE(Booking.start_time) == cron_time.time().minute) \
                                .all()

            for row in result:
                try:
                    # add next appointment
                    booking_id = row.id
                    request_id = row.request_id

                    # 11번가의 경우 정해진 새로 추가 하지 않는다.
                    if row.source in ['11st', 'auction', 'gmarket'] or row.user_type in ['11st', 'auction', 'gmarket']:
                        continue

                    # 전체 취소인 경우가 아닐 때만 새로 추가한다.
                    if self.is_cancelled_all(booking_id):
                        continue

                    org_master_id = self.get_org_master(request_id)

                    appointment_type = row.appointment_type
                    user_id = row.user_id
                    master_id = org_master_id if org_master_id != None else row.master_id
                    additional_task = row.additional_task
                    cleaning_duration = row.cleaning_duration
                    booking_time = dt.datetime.now()
                    price = row.price
                    price_with_task = row.price_with_task
                    card_idx = userdao.get_user_default_card_index(user_id)
                    addr_idx = row.addr_idx
                    message = row.message
                    trash_location = row.trash_location
                    laundry_apply_all = self.get_last_laundry_all(request_id)
                    enterhome = row.enterhome
                    enterbuilding = row.enterbuilding
                    havetools = row.havetools
                    havepet = row.havepet
                    is_dirty = row.is_dirty
                    master_gender = row.master_gender
                    wage_per_hour = row.wage_per_hour
                    status = row.status
                    cleaning_status = row.cleaning_status
                    routing_method = row.routing_method
                    source = row.source
                    user_type = row.user_type

                    actual_price = price
                    if havetools == 1:
                        additional_task = 0
                    else:
                        additional_task = 64
                        #actual_price += BC.VACCUM_CHARGE

                    if laundry_apply_all == 1:
                        additional_task += 4 # 빨래

                    print 'booking_id', booking_id
                    print 'user_id', user_id, 'master_id', master_id, 'price', price, 'request_id', request_id

                    # get next appointment info
                    start_time, estimated_end_time = self.get_next_appointment_date(request_id, appointment_type)
                    appointment_index = self.get_next_appointment_index(request_id, cleaning_status, appointment_type)

                    # add appointment
                    self.add_new_appointment(request_id, master_id, user_id, appointment_type, appointment_index,
                                            booking_time, start_time, estimated_end_time, cleaning_duration, additional_task, price, actual_price,
                                            card_idx, addr_idx, message, trash_location, enterhome, enterbuilding, routing_method, havetools,
                                            havepet, laundry_apply_all, is_dirty, master_gender, wage_per_hour, source, user_type)
                except Exception, e:
                    session.rollback()
                    print_err_detail(e)
                    continue

        except Exception, e:
            session.rollback()
            print_err_detail(e)

        finally:
            session.close()



if __name__ == '__main__':
    job = BookingPaymentJob()
    job.charge()
    job.add_upcoming()
