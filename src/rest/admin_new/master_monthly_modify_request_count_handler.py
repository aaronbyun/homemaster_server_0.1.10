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
from bson.timestamp import Timestamp
from data.session.mysql_session import engine, Session
from data.model.data_model import MasterBookingModifyRequest
from data.dao.masterdao import MasterDAO
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.encryption import aes_helper as aes
from utils.datetime_utils import convert_datetime_format2

class MasterMonthlyRequestCountHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        master_id = self.get_argument('master_id', '')
        month     = self.get_argument('month', 0)

        print master_id, month
        month = int(month)
        if month == 0:
            month = dt.datetime.now().month

        ret = {}

        try:
            session = Session()

            row = session.query(func.count(MasterBookingModifyRequest)) \
                        .filter(MasterBookingModifyRequest.master_id == master_id) \
                        .filter(func.month(MasterBookingModifyRequest.request_time) == month ) \
                        .one()

            count = row[0]

            ret['response'] = count
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()
            self.write(json.dumps(ret))
