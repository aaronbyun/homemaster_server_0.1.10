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
import pickle
import datetime as dt
import booking_constant as BC
from schedule.schedule_helper import HMScheduler
from sqlalchemy import func, or_, and_
from nptime import nptime
from utils.datetime_utils import time_to_str, timedelta_to_time, time_to_minutes
from utils.geo_utils import get_moving_time
from data.session.mysql_session import engine, Session
from data.intermediate.value_holder import IntermediateValueHolder
from data.model.data_model import UserPaymentRecord, Booking, UserDefaultAddress, UserDefaultCard
from data.dao.userdao import UserDAO
from data.dao.addressdao import AddressDAO
from data.dao.masterdao import MasterDAO
from err.error_handler import print_err_detail, err_dict
from response import Response
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from data.intermediate.value_holder import IntermediateValueHolder
from response import add_err_message_to_response, add_err_ko_message_to_response
from sqlalchemy.exc import IntegrityError
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel
from sender.alimtalk_sender import send_alimtalk
from sender.push_sender import send_booking_schedule_updated
from utils.datetime_utils import convert_datetime_format2

from payment.payment_helper import request_payment, cancel_payment

try:
    from utils.secrets import MANAGERS_CALL
except ImportError:
    MANAGERS_CALL = ''


class UpdateScheduleHandler(tornado.web.RequestHandler):
    def get_amount_day_of_week_change(self, org_date, sel_date):
        if org_date.weekday() in BC.WEEKDAYS and sel_date.weekday() in BC.WEEKEND:
            return 10000
        elif org_date.weekday() in BC.WEEKEND and sel_date.weekday() in BC.WEEKDAYS:
            return -10000
        else:
            return 0

    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        ret = {}

        booking_id                  = self.get_argument('booking_id', '')

        uid                         = self.get_argument('uid', '')
        date                        = self.get_argument('date', dt.datetime.strftime(dt.datetime.now(), '%Y%m%d'))
        time                        = self.get_argument('time', '08:00')
        master_ids                  = self.get_argument('master_ids', [])
        apply_to_all_behind         = self.get_argument('apply_to_all_behind', 0)
        by_manager                  = self.get_argument('by_manager', 0)

        # convert parameters
        apply_to_all_behind         = int(apply_to_all_behind)
        selected_date_str           = date
        time_str                    = time
        selected_date               = dt.datetime.strptime(date, '%Y%m%d')
        master_ids                  = master_ids.split(',')
        by_manager                  = int(by_manager)

        # logging part
        mix = get_mixpanel()
        mongo_logger = get_mongo_logger()

        print 'update schedule'
        print selected_date_str, time_str, apply_to_all_behind
        print '*' * 100

        try:
            session = Session()

            booking_info = {}

            userdao     = UserDAO()
            masterdao   = MasterDAO()
            holder      = IntermediateValueHolder()

            try:
                row = session.query(Booking).filter(Booking.id == booking_id).one()
            except NoResultFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_no_record'])
                return

            except MultipleResultsFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_multiple_record'])
                return


            request_id              = row.request_id
            user_id                 = row.user_id
            user_name               = userdao.get_user_name(user_id)
            appointment_type        = row.appointment_type
            appointment_index       = row.appointment_index
            additional_task         = row.additional_task
            org_master_id           = row.master_id
            org_start_time          = row.start_time
            org_estimated_end_time  = row.estimated_end_time
            payment_status          = row.payment_status
            price_with_task         = row.price_with_task

            # 결제가 된 경우, 상황에 따라
            if payment_status == BC.BOOKING_PAID \
                                            and not userdao.is_b2b(user_id) \
                                            and row.source == 'hm':

                amount = self.get_amount_day_of_week_change(org_start_time, selected_date)
                if amount != 0:
                    ret_code, msg = cancel_payment(user_id, booking_id, price_with_task, '0', 'weeked_update_cancel')
                    if ret_code == True:
                        new_price = price_with_task + amount
                        ret_code, msg = request_payment(user_id, user_name, booking_id, new_price, appointment_type, status = 'PAID')
                        if ret_code == True:
                            row.payment_status = BC.BOOKING_PAID
                            row.tid = msg
                        else:
                            row.payment_status = BC.BOOKING_PAYMENT_FAILED

            duration = time_to_minutes(timedelta_to_time(org_estimated_end_time - org_start_time))

            if appointment_type == BC.ONE_TIME_BUT_CONSIDERING:
                appointment_type = BC.ONE_TIME

            if apply_to_all_behind == 0: # 단일 적용이라면
                appointment_type = BC.ONE_TIME

            count_of_iteration = appointment_type * 2 + 2 # 2 months

            # 편집 에러 기존 예약은 무조건 4개인데, 편집시 3개만 생성해서 에러가 발생
            # 꼼수로 4주 1회인 경우, iteration하나 늘림.
            if appointment_type == BC.ONE_TIME_A_MONTH:
                count_of_iteration += 1

            date_list = []
            for i in xrange(count_of_iteration):
                if appointment_type == 0:
                    appointment_type = 4

                date = selected_date + dt.timedelta(weeks = (4 / appointment_type) * i)
                date = dt.datetime.strftime(date, '%Y%m%d')
                date_list.append(date)


            booking_info['dates']            = date_list
            booking_info['time']             = time

            # 각 마스터별로 예약이 가능한지 메모리에서 다시 한번 확인.
            # 선택한 값을 메모리에 키로 저장하여 중복되는 예약 방지.
            # 선택 했으면 선택된 정보를 가지고 있어야 함
            master_num = len(master_ids)

            i = 0
            while i < master_num: # 랭킹이 높은 홈마스터별로 확인
                mid = master_ids[i]
                master_date_keys = []

                # 날짜별 키 생성
                for date in date_list:
                    key = '%s_%s' % (mid, date)
                    master_date_keys.append(key)

                # 저장할 키 생성
                booking_item_key = '%s_%s_%d' % (user_id, master_date_keys[0], appointment_type)

                if holder.store_keys(master_date_keys) and not masterdao.is_master_off_date(mid, selected_date.date()): # 메모리에 키가 하나도 없을 때, 즉 예약이 가능할 때
                    holder.store(booking_item_key, booking_info)

                    #master_date_keys = ','.join(master_date_keys)

                    if apply_to_all_behind == 0 or appointment_type == 0: # 1회성
                        booking_time       = dt.time(hour = int(time.split(':')[0]), minute = int(time.split(':')[1]))
                        start_time         = dt.datetime.combine(selected_date.date(), booking_time)

                        org_master_id   =  row.master_id
                        changed_master_id = mid

                        row.start_time          = start_time
                        row.estimated_end_time  = start_time + dt.timedelta(minutes = duration)
                        row.master_id           = mid
                        row.additional_task     = additional_task

                        if org_master_id != mid: # 기존 마스터님과 다르면
                            row.is_master_changed = 1

                        bid             = row.id
                        org_time        = convert_datetime_format2(org_start_time)
                        changed_time    = convert_datetime_format2(start_time)

                        amount = self.get_amount_day_of_week_change(org_start_time, selected_date)

                        row.price           += amount
                        row.price_with_task += amount
                        # 추가 결제 하거나, 부분 취소로 대체

                        mongo_logger.debug('update logs', extra = {'user_id' : user_id,
                                        'org_time' : org_time, 'changed_time' : changed_time,
                                        'booking_id' : bid, 'apply_to_all_behind' : apply_to_all_behind,
                                        'org_master_id' : org_master_id, 'changed_master_id' : changed_master_id,
                                        'by_manager' : by_manager})
                    else: # 전체 변경

                        print "idx", appointment_index
                        all_bookings = session.query(Booking) \
                                            .filter(Booking.request_id == request_id) \
                                            .filter(Booking.appointment_index >= appointment_index) \
                                            .filter(Booking.cleaning_status > BC.BOOKING_CANCELED) \
                                            .order_by(Booking.start_time) \
                                            .all()

                        former_bookings = session.query(Booking) \
                                            .filter(Booking.request_id == request_id) \
                                            .filter(Booking.appointment_index < appointment_index) \
                                            .order_by(Booking.start_time) \
                                            .all()

                        for former in former_bookings:
                            former.is_master_changed = 1

                        amount = self.get_amount_day_of_week_change(org_start_time, selected_date)

                        index = 0
                        for booking in all_bookings:
                            print 'booking udate loop'
                            if booking.cleaning_status != BC.BOOKING_COMPLETED and booking.cleaning_status != BC.BOOKING_STARTED:
                                booking.is_master_changed   = 0

                                booking_time       = dt.time(hour = int(time.split(':')[0]), minute = int(time.split(':')[1]))
                                start_time         = dt.datetime.combine(dt.datetime.strptime(date_list[index], '%Y%m%d'), booking_time)

                                org_start_time          = booking.start_time
                                org_estimated_end_time  = booking.estimated_end_time

                                duration = time_to_minutes(timedelta_to_time(org_estimated_end_time - org_start_time))

                                org_master_id   =  booking.master_id
                                changed_master_id = mid

                                booking.master_id           = mid
                                booking.org_start_time      = start_time
                                booking.start_time          = start_time
                                booking.estimated_end_time  = start_time + dt.timedelta(minutes = duration)
                                booking.price           += amount
                                booking.price_with_task += amount

                                bid             = booking.id
                                org_time        = convert_datetime_format2(org_start_time)
                                changed_time    = convert_datetime_format2(start_time)

                                '''
                                mongo_logger.debug('update logs', extra = {'user_id' : user_id,
                                                'org_time' : org_time, 'changed_time' : changed_time,
                                                'booking_id' : bid, 'apply_to_all_behind' : apply_to_all_behind,
                                                'org_master_id' : org_master_id, 'changed_master_id' : changed_master_id,
                                                'by_manager' : by_manager})
                                '''

                                index += 1
                            else:
                                continue


                    ret['response'] = Response.SUCCESS
                    self.set_status(Response.RESULT_OK)

                    session.commit()

                    holder.remove(booking_item_key)
                    for sk in master_date_keys:
                        print 'key : ', sk
                        holder.remove(sk)

                    user_name = userdao.get_user_name(user_id)

                    # manager alimtalk
                    #for manager_phone in MANAGERS_CALL.split(','):
                    #    send_alimtalk(manager_phone, 'noti_manager_modify_date', user_name, selected_date_str + time)

                    #master_pushkey = masterdao.get_master_pushkey(mid)
                    #send_booking_schedule_updated('android', [master_pushkey], booking_id, selected_date_str + ' ' + time_str)

                    # log to mixpanel
                    mix.track(user_id, 'update schedule', {'user_id' : user_id, 'date' : selected_date_str, 'time' : time, 'booking_id' : booking_id, 'apply_to_all_behind' : apply_to_all_behind})

                    # log to mongo
                    mongo_logger.debug('update schedule', extra = {'user_id' : user_id, 'date' : selected_date_str, 'time' : time, 'booking_id' : booking_id, 'apply_to_all_behind' : apply_to_all_behind})
                    return

                i += 1

            # log to mixpanel
            mix.track(user_id, 'cannot update schedule', {'time' : dt.datetime.now(), 'user_id' : user_id, 'date' : selected_date_str, 'time' : time, 'apply_to_all_behind' : apply_to_all_behind})

            # log to mongo
            mongo_logger.debug('cannot update schedule', extra = {'user_id' : user_id, 'date' : selected_date_str, 'time' : time, 'apply_to_all_behind' : apply_to_all_behind})

            # other users preempt homemasters, so no homemaster available
            self.set_status(Response.RESULT_OK)
            add_err_message_to_response(ret, err_dict['err_homemaster_occupied'])
            return

        except Exception, e:
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)
            mongo_logger.error('error request update schedules', extra = {'user_id' : user_id, 'err' : str(e)})

        finally:
            self.write(json.dumps(ret))
