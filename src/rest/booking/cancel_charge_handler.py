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
import booking_constant as BC
from sqlalchemy import and_, or_
from sender.sms_sender import SMS_Sender
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, Master, User, UserAddress, UserDefaultAddress
from utils.datetime_utils import convert_datetime_format
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from utils.datetime_utils import convert_datetime_format

class CancelChargeHandler(tornado.web.RequestHandler):
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
                add_err_message_to_response(ret, err_dict['err_no_entry_to_cancel'])
                return   

            stmt = session.query(Booking.request_id).filter(Booking.id == booking_id).subquery()
            first_startime = session.query(Booking.start_time).filter(Booking.request_id == stmt).order_by(Booking.start_time).first()[0]



            # 서비스를 처음 이용한지 2달이 넘었는지 아닌지 조사, 
            # 넘지 않았다면 이미 부과된 금액에 대해서도 1회 서비스 금액 과의 차액만큼 부과됨            
            current_time = dt.datetime.now()

            completed_charge = 0
            if current_time < first_startime + dt.timedelta(days=57):
                completed_charge = session.query(Booking).filter(Booking.request_id == stmt).filter(Booking.cleaning_status == BC.BOOKING_COMPLETED).count()


            now = dt.datetime.now()
            start_time  = row.start_time
            price = row.price

            diff_in_hours = (start_time - now).total_seconds() / 3600

            percentage = 0
            if diff_in_hours >= 24:
                charge = price * BC.BOOKING_CHARGE_RATE_NO
                percentage = BC.BOOKING_CHARGE_RATE_NO
            elif 4 <= diff_in_hours < 24:
                charge = price * BC.BOOKING_CHARGE_RATE_30
                percentage = BC.BOOKING_CHARGE_RATE_30
            else:
                charge = price * BC.BOOKING_CHARGE_RATE_ALL
                percentage = BC.BOOKING_CHARGE_RATE_ALL


            ret['response'] = {'charge' : charge, 'percentage' : int(percentage * 100), 'over_two_month' : completed_charge}
            self.set_status(Response.RESULT_OK)
            
        except Exception, e:
            session.rollback()
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()
            self.write(json.dumps(ret))