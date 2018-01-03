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
from sqlalchemy import func
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, UserPushKey, User, MasterPoint
from data.dao.userdao import UserDAO
from rest.booking import booking_constant as BC
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sender.push_sender import send_cleaning_complete_notification
from data.encryption import aes_helper as aes
from sender.alimtalk_sender import send_alimtalk

class ScheduleCompleteWithTimeHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        booking_id = self.get_argument('booking_id', '')
        end_time = self.get_argument('end_time', '')

        ret = {}

        try:
            session = Session()
            userdao = UserDAO()

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

            user_id = row.user_id
            master_id = row.master_id
            row.status = BC.BOOKING_COMPLETED
            row.cleaning_status = BC.BOOKING_COMPLETED
            now = dt.datetime.strftime(row.start_time, '%Y%m%d')
            row.end_time = dt.datetime.strptime(now+end_time, '%Y%m%d%H%M')

            masterpoint = MasterPoint(master_id = master_id, point_index = 0, point = 1, point_date = dt.datetime.now())
            session.add(masterpoint)

            session.commit()

            # cleaning complete push notification
            try:
                push_row = session.query(User, UserPushKey) \
                                .outerjoin(UserPushKey, UserPushKey.user_id == User.id) \
                                .filter(User.id == user_id) \
                                .one()
            except NoResultFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_no_record'])
                self.write(json.dumps(ret))
                return

            except MultipleResultsFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_multiple_record'])
                self.write(json.dumps(ret))
                return

            devicetype = push_row.User.devicetype
            key = userdao.get_user_salt_by_id(user_id)[:16]
            crypto = aes.MyCrypto(key)

            if devicetype == 'android':
                pushkey = push_row.UserPushKey.pushkey
            else:
                pushkey = crypto.decodeAES(push_row.User.phone)

            phone     = crypto.decodeAES(push_row.User.phone)
            user_name = crypto.decodeAES(push_row.User.name)

            send_cleaning_complete_notification(devicetype, [pushkey], booking_id)

            # alim talk
            send_alimtalk(phone, 'noti_complete', user_name)

            print booking_id, 'status updated to complete at :', dt.datetime.now()

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
