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

class ScheduleStartHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")

        booking_id = self.get_argument('booking_id', '')

        ret = {}

        try:
            session = Session()

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

            now = dt.datetime.now()

            row.working_start_time = now
            row.cleaning_status = BC.BOOKING_STARTED

            session.commit()

            print booking_id, 'status updated to started at :', dt.datetime.now()

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