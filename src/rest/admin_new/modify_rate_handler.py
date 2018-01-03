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
from data.model.data_model import Rating
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class ModifyRateHandler(tornado.web.RequestHandler):

    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        ret = {}

        booking_id           = self.get_argument('booking_id', '')
        rate_clean           = self.get_argument('rate_clean', 0)
        rate_master          = self.get_argument('rate_master', 0)

        rate_clean   = float(rate_clean)
        rate_master  = float(rate_master)

        try:
            session = Session()

            try:
                row = session.query(Rating).filter(Rating.booking_id == booking_id).one()

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

            row.rate_clean = rate_clean
            row.rate_master = rate_master
            session.commit()

            print booking_id, ' has successfully modify rate_clean to', rate_clean
            print booking_id, ' has successfully modify rate_master to', rate_master

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
