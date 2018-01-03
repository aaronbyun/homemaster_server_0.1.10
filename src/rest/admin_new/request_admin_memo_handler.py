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
from sqlalchemy import desc
from data.session.mysql_session import engine, Session
from data.model.data_model import AdminMemo
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.encryption import aes_helper as aes
from utils.datetime_utils import convert_datetime_format2

class RequestAdminMemoHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        user_id    = self.get_argument('user_id', '')

        print 'user_id : ' + user_id

        ret = {}

        try:
            session = Session()

            memos = []

            result = session.query(AdminMemo) \
                            .filter(AdminMemo.user_id == user_id) \
                            .order_by(desc(AdminMemo.register_time)) \
                            .all()

            for row in result:
                memo = {}
                memo['reg_time'] = dt.datetime.strftime(row.register_time, '%Y-%m-%d %H:%M')
                memo['memo'] = row.memo
                memos.append(memo)

            ret['response'] = memos
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))
