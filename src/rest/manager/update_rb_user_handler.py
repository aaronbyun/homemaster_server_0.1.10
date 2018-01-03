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
from data.model.data_model import RegularBasisManagement
from data.dao.userdao import UserDAO
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.encryption import aes_helper as aes
from sqlalchemy import func, or_, and_, desc
from utils.datetime_utils import convert_datetime_format2

class UpdateRegularBasisUserHandler(tornado.web.RequestHandler):

    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        booking_id = self.get_argument('booking_id', '')
        try1 = self.get_argument('try1', '')
        try2 = self.get_argument('try2', '')
        try3 = self.get_argument('try3', '')
        memo = self.get_argument('memo', '')

        ret = {}

        try:
            session = Session()
            row = session.query(RegularBasisManagement) \
                    .filter(RegularBasisManagement.booking_id == booking_id) \
                    .first()

            if row == None:
                rbm = RegularBasisManagement(booking_id = booking_id,
                                            try_1st = try1,
                                            try_2nd = try2,
                                            try_3rd = try3,
                                            memo = memo)
                session.add(rbm)
            else:
                row.try_1st = try1
                row.try_2nd = try2
                row.try_3rd = try3
                row.memo = memo

            session.commit()


            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)


        except Exception, e:
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()
            self.write(json.dumps(ret))
