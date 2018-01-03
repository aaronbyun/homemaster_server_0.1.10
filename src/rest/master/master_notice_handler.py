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
from sqlalchemy import and_, or_, func
from data.session.mysql_session import engine, Session
from data.model.data_model import MasterNotice, Master
from data.dao.userdao import UserDAO
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.encryption import aes_helper as aes
from sqlalchemy import desc
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

class MasterNoticeHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        ret = {}

        try:
            session = Session()

            master_notices = []

            results = session.query(MasterNotice) \
                             .filter(MasterNotice.active == 1) \
                             .order_by(desc(MasterNotice.reg_time)) \
                             .all()

            now = dt.datetime.now()

            for result in results:
                master_notice = {}
                is_new = 0
                days = (now - result.reg_time).days

                master_notice['id']       = result.id
                master_notice['title']    = result.title
                master_notice['content']  = result.content
                master_notice['reg_time'] = dt.datetime.strftime(result.reg_time, '%m/%d')

                if days <= 3:
                    is_new = 1

                master_notice['is_new']   = is_new

                master_notices.append(master_notice)

            ret['response'] = master_notices
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))
