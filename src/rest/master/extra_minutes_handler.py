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
from sqlalchemy import and_, desc
from data.session.mysql_session import engine, Session
from data.model.data_model import User, Booking, ExtraTime
from data.dao.userdao import UserDAO
from data.dao.addressdao import AddressDAO
from data.encryption import aes_helper as aes
from response import Response
from response import add_err_message_to_response
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from err.error_handler import print_err_detail, err_dict


class ExtraMinutesHandler(tornado.web.RequestHandler):

    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        booking_id         = self.get_argument('booking_id', '')
        extra_mins         = self.get_argument('extra_mins', 30)

        extra_mins = int(extra_mins)

        ret = {}

        try:
            session = Session()
            userdao = UserDAO()
            addressdao = AddressDAO()

            extra_time = ExtraTime(booking_id = booking_id,
                                   extended_mins = extra_mins,
                                   request_time = dt.datetime.now())

            session.add(extra_time)
            session.commit()

            # 고객 push
            


            # 마스터 급여


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
