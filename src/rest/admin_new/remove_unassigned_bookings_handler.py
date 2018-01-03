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
from sqlalchemy import and_, or_, func, desc
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, User, Master, MasterBookingModifyRequest
from data.dao.userdao import UserDAO
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.encryption import aes_helper as aes
from sqlalchemy import desc
from utils.datetime_utils import convert_datetime_format2

class RemoveUnassignedBookingsHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        request_id = self.get_argument('request_id', '')

        ret = {}

        try:
            session = Session()
            result = session.query(MasterBookingModifyRequest) \
                        .filter(MasterBookingModifyRequest.id == request_id) \
                        .delete()

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
