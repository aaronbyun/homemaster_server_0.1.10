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
import booking_constant as BC
from sqlalchemy import and_, or_, func
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, Master, User
from utils.datetime_utils import convert_datetime_format, timedelta_to_time, time_to_minutes
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel

class MyBookingsHandler(tornado.web.RequestHandler):

    def get_mybookings(self, session, user_id, mode):
        bookings = []

        try:
            if mode == 'upcoming':
                results = session.query(Booking) \
                                .group_by(Booking.request_id) \
                                .having(Booking.user_id == user_id) \
                                .order_by(func.min(Booking.start_time)) \
                                .all()

                for booking_row in results:
                    booking_result = session.query(Booking, Master, User) \
                                            .join(Master, Booking.master_id == Master.id) \
                                            .join(User, Booking.user_id == User.id) \
                                            .filter(Booking.request_id == booking_row.request_id) \
                                            .filter(or_(Booking.cleaning_status == BC.BOOKING_UPCOMMING, Booking.cleaning_status == BC.BOOKING_STARTED)) \
                                            .order_by(Booking.start_time) \
                                            .all()

                    for row in booking_result:
                        try:
                            tooktime = time_to_minutes(timedelta_to_time(row.Booking.estimated_end_time - row.Booking.start_time))
                        except Exception, e:
                            print_err_detail(e)
                            tooktime = 180

                        if row.Booking.appointment_type == BC.ONE_TIME or row.Booking.appointment_type == BC.ONE_TIME_BUT_CONSIDERING:
                            if row.Booking.is_dirty == 1:
                                tooktime -= 120

                        booking = {}
                        booking['id']               = row.Booking.id
                        booking['request_id']       = row.Booking.request_id
                        booking['index']            = row.Booking.appointment_index
                        booking['devicetype']       = row.User.devicetype
                        booking['datetime']         = convert_datetime_format(row.Booking.start_time)
                        booking['tooktime']         = int(tooktime / 6) # to make 2.5 to 25
                        booking['additional_task']  = row.Booking.additional_task
                        booking['master_name']      = row.Master.name if row.Master != None else ''
                        booking['master_img_url']   = row.Master.img_url if row.Master != None else ''

                        bookings.append(booking)

            elif mode == 'cancel':
                results = session.query(Booking) \
                                .group_by(Booking.request_id) \
                                .having(Booking.user_id == user_id) \
                                .order_by(func.min(Booking.start_time)) \
                                .all()

                for booking_row in results:
                    booking_result = session.query(Booking, Master, User) \
                                            .join(Master, Booking.master_id == Master.id) \
                                            .join(User, Booking.user_id == User.id) \
                                            .filter(Booking.request_id == booking_row.request_id) \
                                            .filter(Booking.cleaning_status == BC.BOOKING_CANCELED) \
                                            .order_by(Booking.start_time) \
                                            .all()
                    for row in booking_result:
                        try:
                            tooktime = time_to_minutes(timedelta_to_time(row.Booking.estimated_end_time - row.Booking.start_time))
                        except Exception, e:
                            print_err_detail(e)
                            tooktime = 180

                        if row.Booking.appointment_type == BC.ONE_TIME or row.Booking.appointment_type == BC.ONE_TIME_BUT_CONSIDERING:
                            if row.Booking.is_dirty == 1:
                                tooktime -= 120

                        booking = {}
                        booking['id']               = row.Booking.id
                        booking['request_id']       = row.Booking.request_id
                        booking['index']            = row.Booking.appointment_index
                        booking['devicetype']       = row.User.devicetype
                        booking['datetime']         = convert_datetime_format(row.Booking.start_time)
                        booking['tooktime']         = int(tooktime / 6) # to make 2.5 to 25
                        booking['additional_task']  = row.Booking.additional_task
                        booking['master_name']      = row.Master.name if row.Master != None else ''
                        booking['master_img_url']   = row.Master.img_url if row.Master != None else ''

                        bookings.append(booking)
            elif mode == 'past':
                now = dt.datetime.now()
                results = session.query(Booking) \
                                .group_by(Booking.request_id) \
                                .having(Booking.user_id == user_id) \
                                .order_by(func.min(Booking.start_time)) \
                                .all()

                for booking_row in results:
                    booking_result = session.query(Booking, Master) \
                                            .join(Master, Booking.master_id == Master.id) \
                                            .filter(Booking.request_id == booking_row.request_id) \
                                            .filter(Booking.cleaning_status == BC.BOOKING_COMPLETED) \
                                            .order_by(Booking.start_time) \
                                            .all()
                    for row in booking_result:
                        try:
                            tooktime = time_to_minutes(timedelta_to_time(row.Booking.estimated_end_time - row.Booking.start_time))
                        except Exception, e:
                            print_err_detail(e)
                            tooktime = 180

                        #if row.Booking.appointment_type == BC.ONE_TIME or row.Booking.appointment_type == BC.ONE_TIME_BUT_CONSIDERING:
                        #    if row.Booking.is_dirty == 1:
                        #        tooktime -= 120

                        # 클리닝 및 홈마스터 평가를 클리닝 후 2일 이내로 제한 두기
                        havereview = row.Booking.havereview
                        if row.Booking.havereview == 0:
                            diff = now - row.Booking.end_time
                            havereview = 0 if diff.days < 2 else 1

                        booking = {}
                        booking['id']               = row.Booking.id
                        booking['request_id']       = row.Booking.request_id
                        booking['index']            = row.Booking.appointment_index
                        booking['datetime']         = convert_datetime_format(row.Booking.start_time)
                        booking['tooktime']         = int(tooktime / 6) # to make 2.5 to 25
                        booking['havereview']       = havereview
                        booking['additional_task']  = row.Booking.additional_task
                        booking['master_name']      = row.Master.name if row.Master != None else ''
                        booking['master_img_url']   = row.Master.img_url if row.Master != None else ''

                        bookings.append(booking)

        except Exception, e:
            print_err_detail(e)
            raise Exception(e)

        return bookings

    def get(self, **params):
        self.set_header("Content-Type", "application/json")

        user_id = self.get_argument('id', '')
        mode    = params['mode']

        ret = {}

        mongo_logger = get_mongo_logger()
        mix = get_mixpanel()

        try:
            session = Session()

            bookings = self.get_mybookings(session, user_id, mode)
            ret['response'] = bookings
            self.set_status(Response.RESULT_OK)

            mix.track(user_id, 'got booking info', {'time' : dt.datetime.now(), 'mode' : mode})
            mongo_logger.debug('got booking info', extra = {'uid' : user_id})

            print user_id, 'successfully retrieved upcomming events...', dt.datetime.now()

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()
            self.write(json.dumps(ret))
