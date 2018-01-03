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
from sqlalchemy import func, and_, or_
from booking import booking_constant as BC
from data.session.mysql_session import engine, Session
from data.model.data_model import Master, Booking, User, UserCard, UserDefaultCard, UserDefaultAddress, UserAddress, MasterTimeSlot, Promotion, EventPromotionBooking
from data.dao.userdao import UserDAO
from data.dao.masterdao import MasterDAO
from data.encryption import aes_helper as aes
from response import Response
from response import add_err_message_to_response
from utils.datetime_utils import time_to_str2
from err.error_handler import print_err_detail, err_dict

# hm_schedule_ondate
class MasterScheduleTimeOnDateInfoHandler(tornado.web.RequestHandler):
    def make_schedule_dict(self, booking_id, devicetype, appointment_type, appointment_index, start_time, end_time, havereview, user_id, user_name, user_phone, user_addr, size, kind, is_dirty, status, cleaning_status, payment_status, price, discount_price, routing_method, is_b2b, card):
        schedule_dict = {}
        schedule_dict['booking_id']       = booking_id
        schedule_dict['device_type']      = devicetype
        schedule_dict['appointment_type'] = appointment_type
        schedule_dict['appointment_index'] = appointment_index
        schedule_dict['start_time']       = start_time
        schedule_dict['end_time']         = end_time
        schedule_dict['havereview']       = havereview
        schedule_dict['user_id']          = user_id
        schedule_dict['user_name']        = user_name
        schedule_dict['user_phone']        = user_phone
        schedule_dict['user_addr']        = user_addr
        schedule_dict['size']             = size
        schedule_dict['kind']             = kind
        schedule_dict['is_dirty']         = is_dirty
        schedule_dict['status']           = status
        schedule_dict['cleaning_status']  = cleaning_status
        schedule_dict['payment_status']   = payment_status
        schedule_dict['price']            = price
        schedule_dict['discount_price']   = discount_price
        schedule_dict['is_routing_method'] = False if routing_method == None else True
        schedule_dict['is_b2b']           = True if is_b2b == 1 else False
        schedule_dict['card']              = 1 if card != None else 0


        return schedule_dict


    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        date = self.get_argument('date', '')
        sigungu = self.get_argument('sigungu', '')
        customer_sigungu = self.get_argument('customer_sigungu', '')

        if date == None or date == '':
            date = dt.datetime.now()

        date = dt.datetime.strptime(date, '%Y%m%d')

        ret = {}

        try:
            session = Session()
            userdao = UserDAO()
            masterdao = MasterDAO()

            if sigungu == '':
              master_ids = masterdao.get_all_master_ids()
            else:
              master_ids = masterdao.get_master_ids_where_regions_available(sigungu)

            master_times = []

            day_of_week = date.weekday()

            for mid in master_ids:
              master_schedules = []

              '''start_times, end_times = masterdao.get_master_working_time(mid)

              start_times = start_times.split(',')
              end_times = end_times.split(',')

              st = start_times[day_of_week] if start_times[day_of_week] != '' else 8
              et = end_times[day_of_week] if end_times[day_of_week] != '' else 8

              st = int(st)
              et = int(et)'''

              st, et = masterdao.get_master_working_time_for_day(mid, date.date())
              current_cleaning_counts = masterdao.get_master_completed_cleaning_count_at_date(mid, date)
              is_unassigned = masterdao.is_unassigned(mid)

              master_dict = {}
              master_dict['master_name'] = masterdao.get_master_name(mid)
              master_dict['master_id'] = mid
              master_dict['is_unassigned'] = is_unassigned
              master_dict['is_beginner'] = True if current_cleaning_counts <= 10 else False
              master_dict['current_cleaning_counts'] = current_cleaning_counts
              master_dict['master_available_from']   = '0%s:00' % st if st < 10 else '%s:00' % st
              master_dict['master_available_to']     = '0%s:00' % et if et < 10 else '%s:00' % et

              # for day off
              master_dict['is_day_off'] = masterdao.is_day_off(mid, date.date())

              for row in session.query(Master, Booking, User, UserAddress, UserDefaultCard, Promotion, EventPromotionBooking) \
                                .outerjoin(Booking, Master.id == Booking.master_id) \
                                .join(User, User.id == Booking.user_id) \
                                .join(UserAddress, and_(Booking.user_id == UserAddress.user_id, Booking.addr_idx == UserAddress.user_addr_index)) \
                                .outerjoin(UserDefaultCard, User.id == UserDefaultCard.user_id) \
                                .outerjoin(Promotion, Booking.id == Promotion.booking_id) \
                                .outerjoin(EventPromotionBooking, Booking.id == EventPromotionBooking.booking_id) \
                                .filter(func.DATE(Booking.start_time) == date) \
                                .filter(Master.id == mid) \
                                .filter(or_(Booking.cleaning_status == BC.BOOKING_UPCOMMING, Booking.cleaning_status == BC.BOOKING_STARTED, Booking.cleaning_status == BC.BOOKING_COMPLETED)) \
                                .order_by(Master.name, Booking.start_time) \
                                .all():

                  key = userdao.get_user_salt_by_id(row.User.id)[:16]
                  crypto = aes.MyCrypto(key)

                  discount_price = 0
                  if row.Promotion != None:
                      discount_price += row.Promotion.discount_price
                  if row.EventPromotionBooking != None:
                      discount_price += row.EventPromotionBooking.discount_price

                  kind = row.UserAddress.kind
                  if kind == 0:
                      kind = '오피스텔'
                  elif kind == 1:
                      kind = '주택'
                  else:
                      kind = '아파트'

                  address = crypto.decodeAES(row.UserAddress.address)
                  if customer_sigungu in address:
                      master_schedules.append(self.make_schedule_dict( row.Booking.id,
                                                                   row.User.devicetype,
                                                                   row.Booking.appointment_type,
                                                                   row.Booking.appointment_index,
                                                                   dt.datetime.strftime(row.Booking.start_time, '%H:%M'),
                                                                   dt.datetime.strftime(row.Booking.estimated_end_time, '%H:%M'),
                                                                   row.Booking.havereview,
                                                                   row.Booking.user_id,
                                                                   crypto.decodeAES(row.User.name),
                                                                   crypto.decodeAES(row.User.phone),
                                                                   crypto.decodeAES(row.UserAddress.address),
                                                                   row.UserAddress.size,
                                                                   kind,
                                                                   row.Booking.is_dirty,
                                                                   row.Booking.status,
                                                                   row.Booking.cleaning_status,
                                                                   row.Booking.payment_status,
                                                                   row.Booking.price_with_task,
                                                                   discount_price,
                                                                   row.Booking.routing_method,
                                                                   row.User.is_b2b,
                                                                   row.UserDefaultCard))


              master_dict['time_list'] = master_schedules
              master_times.append(master_dict)

            ret['response'] = master_times
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))
