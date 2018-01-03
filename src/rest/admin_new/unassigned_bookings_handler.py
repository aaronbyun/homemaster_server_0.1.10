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
from sqlalchemy import and_, or_, func, desc
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, User, Master, MasterBookingModifyRequest
from data.dao.userdao import UserDAO
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.encryption import aes_helper as aes
from sqlalchemy import desc
from utils.datetime_utils import convert_datetime_format2

class UnassignedBookingsHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        ret = {}

        try:
            session = Session()
            userdao = UserDAO()

            unassigned_bookings = []

            # for modify request
            result = session.query(MasterBookingModifyRequest, Booking, Master, User) \
                            .join(Booking, Booking.id == MasterBookingModifyRequest.booking_id) \
                            .join(Master, MasterBookingModifyRequest.master_id == Master.id) \
                            .join(User, Booking.user_id == User.id) \
                            .filter(Booking.cleaning_status == 0) \
                            .order_by(Booking.start_time) \
                            .all()

            for row in result:
                key = userdao.get_user_salt_by_id(row.User.id)[:16]
                crypto = aes.MyCrypto(key)

                print 'request modification bookings list..'
                print row.MasterBookingModifyRequest.org_time
                print row.MasterBookingModifyRequest.master_id
                print row.Booking.master_id
                print row.Booking.start_time

                if row.MasterBookingModifyRequest.org_time != None and \
                    (row.MasterBookingModifyRequest.master_id != row.Booking.master_id or \
                    row.MasterBookingModifyRequest.org_time != row.Booking.start_time):
                    continue

                booking = {}
                booking['id']               = row.MasterBookingModifyRequest.id
                booking['booking_id']       = row.Booking.id
                booking['user_name']        = crypto.decodeAES(row.User.name)
                booking['user_phone']       = crypto.decodeAES(row.User.phone)
                booking['master_name']      = row.Master.name
                booking['start_time']       = convert_datetime_format2(row.Booking.start_time)
                booking['reason']           = row.MasterBookingModifyRequest.reason
                booking['status']           = 'REQUESTED'

                unassigned_bookings.append(booking)

            # for unassigned
            result = session.query(Booking, Master, User) \
                    .join(Master, Booking.master_id == Master.id) \
                    .join(User, Booking.user_id == User.id) \
                    .filter(Master.active == 2) \
                    .filter(Booking.cleaning_status == 0) \
                    .order_by(Booking.start_time) \
                    .all()

            for row in result:
                key = userdao.get_user_salt_by_id(row.User.id)[:16]
                crypto = aes.MyCrypto(key)

                booking = {}
                booking['booking_id']       = row.Booking.id
                booking['user_name']        = crypto.decodeAES(row.User.name)
                booking['user_phone']       = crypto.decodeAES(row.User.phone)
                booking['master_name']      = row.Master.name
                booking['start_time']       = convert_datetime_format2(row.Booking.start_time)
                booking['reason']           = '업무 중단'
                booking['status']           = 'UNASSIGNED'

                unassigned_bookings.append(booking)



            ret['response'] = unassigned_bookings;
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))
