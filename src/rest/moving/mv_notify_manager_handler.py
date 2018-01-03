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
import requests
from data.dao.userdao import UserDAO
from response import Response
from response import add_err_message_to_response
from data.session.mysql_session import engine, Session
from data.model.data_model import MovingCleaningBooking
from err.error_handler import print_err_detail, err_dict
from sender.sms_sender import SMS_Sender
from sender.jandi_sender import send_jandi

try:
    from utils.secrets import COOL_SMS_API_KEYS, COOL_SMS_API_SECRET, MAIN_CALL, JAMES_CALL
except ImportError:
    COOL_SMS_API_KEYS = ''
    COOL_SMS_API_SECRET = ''
    MAIN_CALL = ''
    JAMES_CALL = ''


class MovingCleaningNotifyManagerHandler(tornado.web.RequestHandler):

    def post(self):
        self.set_header("Content-Type", "application/json")

        user_id = self.get_argument('user_id', '')

        ret = {}

        try:
            session = Session()
            userdao = UserDAO()

            addr_idx = userdao.get_user_default_address_index(user_id)

            booking = MovingCleaningBooking(user_id = user_id, addr_idx = addr_idx, datetime = dt.datetime.now())
            session.add(booking)
            session.commit()

            # send sms
            sms_sender = SMS_Sender()
            name = str(userdao.get_user_name(user_id))
            phone = str(userdao.get_user_phone(user_id))
            address, size, kind = userdao.get_user_address_detail(user_id)
            address = str(address)
            if kind == 0:
                kind = '오피스텔'
            elif kind == 1:
                kind = '주택'
            elif kind == 2 :
                kind = '아파트'

            text = '입주청소 예약 문의\n이름: %s\n번호: %s\n주소: %s\n종류: %s\n평수:%d' % (name, phone, address, kind, size)
            #print sms_sender.send_for_manager(sender = MAIN_CALL, mtype = 'lms', to = JAMES_CALL, text = str(text))

            # jandi notification
            send_jandi('MOVING_IN_CLEANING', "이사청소 문의", name + ' 고객님 이사청소 문의', text)

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()
            self.write(json.dumps(ret))
