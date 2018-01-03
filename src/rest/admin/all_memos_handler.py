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
from data.model.data_model import User, UserMemo
from data.dao.userdao import UserDAO
from data.encryption import aes_helper as aes
from response import Response
from response import add_err_message_to_response
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from err.error_handler import print_err_detail, err_dict


class AllMemoInfoHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        try:
            session = Session()
            userdao = UserDAO()

            memos = []

            result = session.query(UserMemo, User) \
                            .join(User, UserMemo.user_id == User.id) \
                            .order_by(desc(UserMemo.requested_datetime)) \
                            .all()
            
            for row in result:
                key = userdao.get_user_salt_by_id(row.User.id)[:16]
                crypto = aes.MyCrypto(key)

                memo = {}
                memo['time'] = dt.datetime.strftime(row.UserMemo.requested_datetime, '%Y-%m-%d %H:%M')
                memo['memo'] = row.UserMemo.memo
                memo['user_name'] = crypto.decodeAES(row.User.name)
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