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
from data.model.data_model import Master
from data.dao.masterdao import MasterDAO
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import func


class MasterNamesHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        master_ids     = self.get_argument('master_ids', '')
        ret = {}

        try:
            master_name_dict = {}

            masterdao = MasterDAO()
            master_ids = master_ids.split(',')
            for mid in master_ids:
                master_name = masterdao.get_master_name(mid)
                master_name_dict[mid] = master_name

            ret['response'] = master_name_dict

            self.set_status(Response.RESULT_OK)

        except Exception, e:
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            self.write(json.dumps(ret))
