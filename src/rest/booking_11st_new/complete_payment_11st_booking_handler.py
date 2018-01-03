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

from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.dao.userdao import UserDAO
from data.dao.addressdao import AddressDAO
from data.session.mysql_session import engine, Session
from data.model.data_model import UserCoupon, Booking, OrderID11st
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from utils.geo_utils import get_latlng_from_address, get_geohash
from data.encryption import aes_helper as aes
from sqlalchemy import and_, or_, func
from utils.datetime_utils import convert_datetime_format
from rest.booking import booking_constant as BC
from data.mixpanel.mixpanel_helper import get_mixpanel
from check_11st_booking_daemon import Booking11stChecker

#get_payment_done_11st
class Complete11stPaymentBookingHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        ret = {}

        try:
            time_query = dt.datetime.now() - dt.timedelta(days = 3)
            query_date = time_query
            time_query = time_query.date()

            session = Session()
            records = session.query(OrderID11st.div_no) \
                            .filter(func.date(OrderID11st.datetime) >= time_query) \
                            .all()

            div_nos = [row[0] for row in records]

            now = dt.datetime.now()

            booking_checker = Booking11stChecker()
            orders, result_code, result_msg = booking_checker.check_11st_new_orders(query_date)

            # 예약 들어간 사항 필터링
            orders = [order for order in orders if order['dlvNo'] not in div_nos]

            ret['response'] = {'orders' : orders, 'result_code' : result_code,
                                'result_msg' : result_msg}

            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)

        finally:
            session.close()
            self.write(json.dumps(ret))
            return
