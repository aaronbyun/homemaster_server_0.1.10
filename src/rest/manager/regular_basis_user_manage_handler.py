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
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, User, UserAddress, RegularBasisManagement
from data.dao.userdao import UserDAO
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.encryption import aes_helper as aes
from sqlalchemy import func, or_, and_, desc
from sqlalchemy.orm import aliased
from utils.datetime_utils import convert_datetime_format2

class RegularBasisUserManageHandler(tornado.web.RequestHandler):

    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        year = self.get_argument('year', '')
        month = self.get_argument('month', '')

        if year == '' or month == '':
            now = dt.datetime.now()
            year = now.year
            month = now.month

        try:
            year = int(year)
            month = int(month)
        except:
            year = 2017
            month = 2

        ret = {}
        rb_users = []

        userdao = UserDAO()

        try:
            session = Session()
            b1 = aliased(Booking)
            stmt = session.query(b1) \
                        .filter(b1.cleaning_status == 2) \
                        .filter(or_(b1.appointment_type == 1, b1.appointment_type == 2, b1.appointment_type == 4)) \
                        .subquery()

            rows = session.query(Booking, User, UserAddress, RegularBasisManagement) \
                        .join(User, Booking.user_id == User.id) \
                        .join(UserAddress, and_(Booking.user_id == UserAddress.user_id, Booking.addr_idx == UserAddress.user_addr_index)) \
                        .outerjoin(RegularBasisManagement, Booking.id == RegularBasisManagement.booking_id) \
                        .outerjoin(stmt, Booking.user_id == stmt.c.user_id) \
                        .filter(Booking.appointment_index == 1) \
                        .filter(Booking.cleaning_status == 2) \
                        .filter(or_(Booking.appointment_type == 1, Booking.appointment_type == 2, Booking.appointment_type == 4)) \
                        .filter(func.year(Booking.start_time) == year) \
                        .filter(func.month(Booking.start_time) == month) \
                        .filter(User.is_b2b == 0) \
                        .order_by(desc(Booking.start_time)) \
                        .all()

            for row in rows:
                key = userdao.get_user_salt_by_id(row.User.id)[:16]
                crypto = aes.MyCrypto(key)

                appointment_type = row.Booking.appointment_type

                if appointment_type == 1:
                    appointment_type = '4주1회'
                elif appointment_type == 2:
                    appointment_type = '2주1회'
                elif appointment_type == 4:
                    appointment_type = '매주'

                user = {}
                user['booking_id']  = row.Booking.id
                user['name']        = crypto.decodeAES(row.User.name)
                user['phone']       = crypto.decodeAES(row.User.phone)
                user['address']     = crypto.decodeAES(row.UserAddress.address)
                user['reg_date']    = convert_datetime_format2(row.User.dateofreg)
                user['start_time']  = convert_datetime_format2(row.Booking.start_time)
                user['type']        = appointment_type

                user['try_1st']     = row.RegularBasisManagement.try_1st if row.RegularBasisManagement != None else '진행안됨'
                user['try_2nd']     = row.RegularBasisManagement.try_2nd if row.RegularBasisManagement != None else '진행안됨'
                user['try_3rd']     = row.RegularBasisManagement.try_3rd if row.RegularBasisManagement != None else '진행안됨'
                user['memo']        = row.RegularBasisManagement.memo if row.RegularBasisManagement != None else ''

                rb_users.append(user)

            ret['response'] = rb_users
            self.set_status(Response.RESULT_OK)


        except Exception, e:
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()
            self.write(json.dumps(ret))
