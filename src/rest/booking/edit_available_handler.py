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
from data.model.data_model import Booking
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict

class EditAvailableHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        booking_id              = self.get_argument('booking_id', '')

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

            # booking can not be updated within 24 hours ahead
            appointment_time = row.start_time
            current_time = dt.datetime.now()
            diff_in_hours = (appointment_time - current_time).total_seconds() / 3600

            if diff_in_hours < 24:
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_update_not_allowed'])
                return    

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