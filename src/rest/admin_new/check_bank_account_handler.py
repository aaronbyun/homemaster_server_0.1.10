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
from rest.booking import booking_constant as BC
from response import Response
from response import add_err_message_to_response
from data.session.mysql_session import engine, Session
from data.model.data_model import Rating
from salary import salary_helper
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class CheckBankAccountHandler(tornado.web.RequestHandler):

    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        ret = {}

        account_no  = self.get_argument('account_no', '')
        bank_name   = self.get_argument('bank_name', '')

        account_no = account_no.replace('-', '')

        bank_dict = BC.bank_dict
        bank_code = bank_dict[bank_name]

        try:
            status, message = salary_helper.check_account(account_no, bank_code)

            ret['response'] = {'status' : status, 'message' : message}
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            self.write(json.dumps(ret))
