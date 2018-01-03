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

class MasterNoticeRemoveHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        article_id  = self.get_argument('id', '')

        ret = {}

        try:
            session = Session()
            row = session.query(MasterNotice).filter(MasterNotice.id == article_id).one()
            row.active = 0

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
