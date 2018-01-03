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
from rest.booking import booking_constant as BC
from data.dao.userdao import UserDAO
from data.dao.bookingdao import BookingDAO
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, Master, UserPaymentRecord, Promotion, MasterPoint, User, UserAddress
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import func, and_, not_
from err.error_handler import print_err_detail, err_dict
from response import Response
from response import add_err_message_to_response
from data.encryption import aes_helper as aes

class WeeklyIndicatorHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")



        ret = {}

        try:
            session = Session()
            userdao = UserDAO()
            bookingdao = BookingDAO()

            # get last saturday
            now = dt.datetime.now()
            if week != 0:
                offset = ((now.weekday() - FRIDAY) % 7) + (week - 1) * 7
                now -= dt.timedelta(days=offset)

            offset = (now.weekday() - SATURDAY) % 7
            last_saturday = (now - dt.timedelta(days=offset)).date()
            now = now.date()

            # rating
            #

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
