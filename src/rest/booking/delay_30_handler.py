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
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, MasterTimeSlot
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import func

# delay_schedule
class Delay30Handler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        booking_id = self.get_argument('booking_id', '')
        direction  = self.get_argument('direction', '') # forward, #backward

        if direction == '':
            direction = 'forward'

        if not direction in ['forward', 'backward']:
            self.set_status(Response.RESULT_OK)
            add_err_message_to_response(ret, err_dict['invalid_param'])

            return

        ret = {}

        try:
            session = Session()
            row = session.query(Booking).filter(Booking.id == booking_id).one()

            if row.cleaning_status != BC.BOOKING_UPCOMMING:
                self.set_status(Response.RESULT_OK)
                add_err_ko_message_to_response(ret, '다가오는 예약이 아니면 미룰 수 없습니다.')
                return

            master_id = row.master_id
            work_date = row.start_time.date()

            day_of_week = work_date.weekday()

            start_time = row.start_time
            end_time   = row.estimated_end_time

            start_hour = start_time.time().hour
            start_minute = start_time.time().minute

            end_hour = end_time.time().hour
            end_minute = end_time.time().minute

            master_time = session.query(MasterTimeSlot) \
                    .filter(MasterTimeSlot.master_id == master_id) \
                    .filter(MasterTimeSlot.day_of_week == day_of_week) \
                    .one()

            master_start_time = master_time.start_time
            master_end_time = master_time.end_time

            if start_hour <= master_start_time.hour and start_minute == 0 and direction == 'backward':
                self.set_status(Response.RESULT_OK)
                add_err_ko_message_to_response(ret, '홈마스터님 근무 시작 시각은 ' + str(master_start_time.hour) + ' 시 입니다.')
                return

            if end_hour >= master_end_time.hour and direction == 'forward':
                self.set_status(Response.RESULT_OK)
                add_err_ko_message_to_response(ret, '홈마스터님 근무 종료 시각은 ' + str(master_end_time.hour) + ' 시 입니다.')
                return

            #겹치는 다른 일정이 없으면 미룬다.
            if direction == 'backward':
                minutes = -30
                count = session.query(Booking) \
                    .filter(Booking.master_id == master_id) \
                    .filter(func.date(Booking.start_time) == work_date) \
                    .filter(Booking.estimated_end_time < end_time) \
                    .filter(Booking.estimated_end_time >= start_time - dt.timedelta(minutes = 30)) \
                    .filter(Booking.cleaning_status == BC.BOOKING_UPCOMMING) \
                    .count()

            elif direction == 'forward':
                minutes = 30
                count = session.query(Booking) \
                    .filter(Booking.master_id == master_id) \
                    .filter(func.date(Booking.start_time) == work_date) \
                    .filter(Booking.start_time > start_time) \
                    .filter(Booking.start_time <= end_time + dt.timedelta(minutes = 30)) \
                    .filter(Booking.cleaning_status == BC.BOOKING_UPCOMMING) \
                    .count()

            print booking_id, master_id, work_date
            print direction, minutes, count

            if count != 0:
                self.set_status(Response.RESULT_OK)
                add_err_ko_message_to_response(ret, '다른 예약과 겹쳐, 시간을 당기거나 미룰 수 없습니다.')
                return

            row.start_time += dt.timedelta(minutes = minutes)
            row.estimated_end_time += dt.timedelta(minutes = minutes)
            row.end_time = row.estimated_end_time

            session.commit()

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

        except NoResultFound, e:
            self.set_status(Response.RESULT_OK)
            add_err_message_to_response(ret, err_dict['err_no_record'])
            return

        except MultipleResultsFound, e:
            self.set_status(Response.RESULT_OK)
            add_err_message_to_response(ret, err_dict['err_multiple_record'])
            return

        except Exception, e:
            session.rollback()
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()
            self.write(json.dumps(ret))
