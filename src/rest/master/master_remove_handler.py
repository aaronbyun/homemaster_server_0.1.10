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
from sqlalchemy import desc
from response import Response
from response import add_err_message_to_response
from data.dao.userdao import UserDAO
from data.encryption import aes_helper as aes
from data.session.mysql_session import engine, Session
from data.model.data_model import Master, MasterClaim, User
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from utils.datetime_utils import convert_datetime_format2

# /all_master_claim
class MasterRemoveHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        master_id       = self.get_argument('master_id', '')
        remove_status   = self.get_argument('remove_status', 2)

        print master_id, remove_status

        # 0 - remove completely, 2 - cannot get works, but still showed up in list

        remove_status = int(remove_status)
        if remove_status != 0 and remove_status != 2:
            remove_status = 2

        ret = {}

        try:
            session = Session()
            row = session.query(Master).filter(Master.id == master_id).one()
            row.active = remove_status # about to remove, removig but not all work are reassigned to another homemaster yet

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
