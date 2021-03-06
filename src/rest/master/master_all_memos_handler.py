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
from sqlalchemy import and_, desc
from data.session.mysql_session import engine, Session
from data.model.data_model import User, Master, MasterMemo
from data.dao.userdao import UserDAO
from data.encryption import aes_helper as aes
from response import Response
from response import add_err_message_to_response
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from err.error_handler import print_err_detail, err_dict


class AllMasterMemoInfoHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        user_id = self.get_argument('user_id', '')

        ret = {}

        try:
            session = Session()
            userdao = UserDAO()

            memos = []

            result = session.query(MasterMemo, User, Master) \
                            .join(User, MasterMemo.user_id == User.id) \
                            .join(Master, MasterMemo.master_id == Master.id) \
                            .filter(MasterMemo.user_id == user_id) \
                            .order_by(desc(MasterMemo.datetime)) \
                            .all()

            for row in result:
                memo = {}
                memo['time'] = dt.datetime.strftime(row.MasterMemo.datetime, '%Y-%m-%d %H:%M')
                memo['memo'] = row.MasterMemo.memo
                memo['master_name'] = row.Master.name
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
