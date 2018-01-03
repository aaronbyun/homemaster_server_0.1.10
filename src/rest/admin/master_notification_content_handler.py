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
from data.dao.userdao import UserDAO
from data.dao.masterdao import MasterDAO
from data.encryption import aes_helper as aes
import booking.booking_constant as BC
from sqlalchemy import func, or_, and_
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, Master, User, UserAddress
from response import Response
from response import add_err_message_to_response
from utils.datetime_utils import timedelta_to_time, convert_datetime_format2
from err.error_handler import print_err_detail, err_dict
from sender.sms_sender import additional_task_string

try:
    from utils.secrets import COOL_SMS_API_KEYS, COOL_SMS_API_SECRET, MAIN_CALL, MANAGERS_CALL
except ImportError:
    COOL_SMS_API_KEYS = ''
    COOL_SMS_API_SECRET = ''
    MAIN_CALL = ''
    MANAGERS_CALL = ''

try:
    from utils.stipulation_text import BOOKING_TYPE_DICT, BOOKING_CONFIRM_TEXT, CONFIRM_UPDATE_BODY, BOOKING_UPDATE_TEXT, BOOKING_TEXT_SUBJECT, BOOKING_MASTER_HOUR, UNAVAILABLE_USERS, NOTIFY_TEXT_SUBJECT
except ImportError:
    BOOKING_TYPE_DICT = {}
    BOOKING_CONFIRM_TEXT = ''
    CONFIRM_UPDATE_BODY = ''
    BOOKING_UPDATE_TEXT = ''
    BOOKING_TEXT_SUBJECT = ''
    BOOKING_MASTER_HOUR = ''
    UNAVAILABLE_USERS = ''
    NOTIFY_TEXT_SUBJECT = ''


class MasterNotificationContentHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")

        master_id   = self.get_argument('master_id', '')
        date        = self.get_argument('date', '')

        ret = {}

        date = dt.datetime.strptime(date, '%Y%m%d')

        try:
            session = Session()
            userdao = UserDAO()
            masterdao = MasterDAO()

            content = ''
            result = session.query(Booking, Master, User, UserAddress) \
                            .join(Master, Booking.master_id == Master.id) \
                            .join(User, Booking.user_id == User.id) \
                            .join(UserAddress, and_(Booking.user_id == UserAddress.user_id, Booking.addr_idx == UserAddress.user_addr_index)) \
                            .filter(Booking.master_id == master_id) \
                            .filter(func.date(Booking.start_time) == date) \
                            .filter(or_(Booking.cleaning_status == BC.BOOKING_UPCOMMING, Booking.cleaning_status == BC.BOOKING_COMPLETED)) \
                            .order_by(Booking.start_time) \
                            .all()

            word_idx = 1

            master_name = masterdao.get_master_name(master_id)
            master_phone = masterdao.get_master_phone(master_id)

            for row in result:
                key = userdao.get_user_salt_by_id(row.User.id)[:16]
                crypto = aes.MyCrypto(key)
                master_phone        = str(row.Master.phone)
                master_name         = str(row.Master.name)
                user_name           = str(crypto.decodeAES(row.User.name))
                appointment_index   = str(row.Booking.appointment_index)
                enterbuilding       = str(crypto.decodeAES(row.Booking.enterbuilding)) if row.Booking.enterbuilding != None else str('')
                enterhome           = str(crypto.decodeAES(row.Booking.enterhome))     if row.Booking.enterhome != None else str('')
                date_str            = str(convert_datetime_format2(row.Booking.start_time))
                address             = str(crypto.decodeAES(row.UserAddress.address))
                appointment_type    = str(4 / row.Booking.appointment_type) + '주' \
                                      if row.Booking.appointment_type != BC.ONE_TIME \
                                      and row.Booking.appointment_type != BC.ONE_TIME_BUT_CONSIDERING \
                                      else '1회'
                additional_task     = additional_task_string(row.Booking.additional_task)
                take_time           = timedelta_to_time(row.Booking.estimated_end_time - row.Booking.start_time)
                take_time_str       = '%d시간 %d분' % (take_time.hour, take_time.minute)
                message             = str(row.Booking.message)
                trash_location      = str(row.Booking.trash_location)

                text = CONFIRM_UPDATE_BODY % (user_name, appointment_index, date_str, address, appointment_type, additional_task, take_time_str, enterbuilding, enterhome, message, trash_location)

                content += str(word_idx) + '. ' + str(text) + '\n\n'
                word_idx += 1

            booking_date = dt.datetime.strftime(date, '%m월%d일')
            title = '%s 홈마스터님, %s 일정입니다.' % (master_name, booking_date)

            if word_idx == 1:
                content = '홈마스터님 내일 일정은 없습니다.'
                title = '홈마스터님 내일 일정은 없습니다.'

            ret['response'] = {'content' : content, 'phone' : master_phone, 'subject' : title}
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))