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
import pytz
import booking.booking_constant as BC
from response import Response
from response import add_err_message_to_response
from sqlalchemy import func, and_, or_
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, User, UserAddress, MasterScheduleByDate, MasterBookingModifyRequest
from data.dao.userdao import UserDAO
from data.encryption import aes_helper as aes
from utils.datetime_utils import convert_datetime_format, timedelta_to_time, time_to_minutes, convert_time_format
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from utils.address_utils import convert_to_jibun_address



# master_schedule_ondate
class MasterScheduleOnDateHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        date        = self.get_argument('date')
        master_id   = self.get_argument('master_id', '')

        # convert arguments
        date = dt.datetime.strptime(date, '%Y%m%d')

        try:
            session = Session()
            userdao = UserDAO()

            result = session.query(Booking, User, UserAddress) \
                            .join(User, Booking.user_id == User.id) \
                            .join(UserAddress, and_(Booking.user_id == UserAddress.user_id, Booking.addr_idx == UserAddress.user_addr_index)) \
                            .filter(Booking.master_id == master_id) \
                            .filter(func.date(Booking.start_time) == date) \
                            .filter(or_(Booking.cleaning_status == BC.BOOKING_UPCOMMING, Booking.cleaning_status == BC.BOOKING_STARTED, Booking.cleaning_status == BC.BOOKING_COMPLETED)) \
                            .order_by(Booking.start_time) \
                            .all()

            booking_list = []

            for row in result:
                key = userdao.get_user_salt_by_id(row.Booking.user_id)[:16]
                crypto = aes.MyCrypto(key)

                booking = {}

                tooktime = time_to_minutes(timedelta_to_time(row.Booking.estimated_end_time - row.Booking.start_time))

                if row.Booking.appointment_type == BC.ONE_TIME or row.Booking.appointment_type == BC.ONE_TIME_BUT_CONSIDERING:
                    if row.Booking.is_dirty == 1:
                        tooktime -= 120

                start_time = row.Booking.start_time

                request_count = session.query(MasterBookingModifyRequest) \
                        .filter(MasterBookingModifyRequest.master_id == master_id) \
                        .filter(MasterBookingModifyRequest.booking_id == row.Booking.id) \
                        .filter(MasterBookingModifyRequest.org_time == start_time) \
                        .count()

                booking['booking_id']       = row.Booking.id
                booking['start_time']       = convert_time_format(row.Booking.start_time.time())
                booking['name']             = crypto.decodeAES(row.User.name)
                booking['address']          = crypto.decodeAES(row.UserAddress.address)
                #booking['jibun_address']    = convert_to_jibun_address(booking['address'])
                booking['size']             = row.UserAddress.size
                booking['kind']             = row.UserAddress.kind
                booking['additional_task']  = row.Booking.additional_task
                booking['appointment_type'] = row.Booking.appointment_type
                booking['index']            = row.Booking.appointment_index
                booking['tooktime']         = int(tooktime / 6)
                booking['status']           = row.Booking.status
                booking['cleaning_status']  = row.Booking.cleaning_status
                booking['payment_status']   = row.Booking.payment_status
                booking['is_dirty']         = row.Booking.is_dirty
                booking['request_modify']   = request_count

                booking_list.append(booking)

            dayoff       = False
            is_open_time = False
            free_from    = None
            free_to      = None

            row = session.query(MasterScheduleByDate) \
                    .filter(MasterScheduleByDate.master_id == master_id) \
                    .filter(MasterScheduleByDate.date == date) \
                    .first()

            if row != None:
                if row.active == 0:
                    dayoff = True

                is_open_time = True
                free_from = row.free_from.strftime('%H:%M')
                free_to   = row.free_to.strftime('%H:%M')


            ret['response'] = {'booking_list' : booking_list, 'free_from' : free_from, 'free_to' : free_to, 'is_open_time' : is_open_time, 'dayoff' : dayoff}
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()
            self.write(json.dumps(ret))
