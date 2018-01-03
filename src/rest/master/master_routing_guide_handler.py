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
from response import Response
from response import add_err_message_to_response
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import func

# master_guide_route
class MasterRoutingGuideHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        booking_id     = self.get_argument('booking_id', '')
        routing_method = self.get_argument('routing_method', '')

        ret = {}

        try:
            session = Session()

            stmt = session.query(Booking.request_id).filter(Booking.id == booking_id).subquery()
            result = session.query(Booking).filter(Booking.request_id == stmt) \
                                    .order_by(Booking.start_time) \
                                    .all()


            for row in result:
                row.routing_method = routing_method

            session.commit()

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
