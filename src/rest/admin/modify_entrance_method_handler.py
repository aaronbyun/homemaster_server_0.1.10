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
from data.model.data_model import Booking
from data.dao.userdao import UserDAO
from rest.booking import booking_constant as BC
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from data.encryption import aes_helper as aes

class ModifyEntranceMethodHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        booking_id      = self.get_argument('booking_id', '')
        enterhome       = self.get_argument('enterhome', '')
        enterbuilding   = self.get_argument('enterbuilding', '')

        ret = {}

        try:
            userdao = UserDAO()
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

            request_id = row.request_id
            user_id = row.user_id

            key = userdao.get_user_salt_by_id(user_id)[:16]
            crypto = aes.MyCrypto(key)
            encrypted_enterhome = crypto.encodeAES(str(enterhome))
            encrypted_enterbuilding = crypto.encodeAES(str(enterbuilding))

            result = session.query(Booking).filter(Booking.request_id == request_id).all()
            for booking_row in result:
                booking_row.enterhome = encrypted_enterhome
                booking_row.enterbuilding = encrypted_enterbuilding

            session.commit()

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

            print booking_id, 'was updated entherhome, enterbuilding', dt.datetime.now()

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))
