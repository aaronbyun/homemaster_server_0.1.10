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
from bson.timestamp import Timestamp
from data.session.mysql_session import engine, Session
from data.model.data_model import AdminMemo
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.encryption import aes_helper as aes
from utils.datetime_utils import convert_datetime_format2

class InputAdminMemoHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        user_id    = self.get_argument('user_id', '')
        memo       = self.get_argument('memo', '')

        print 'user_id : ' + user_id
        print 'memo : ' + memo

        ret = {}

        try:
            session = Session()

            admin_memo = AdminMemo(user_id = user_id, memo = memo, register_time = dt.datetime.now())
            session.add(admin_memo)
            session.commit()

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            self.write(json.dumps(ret))
