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
from data.model.data_model import User, UserPushKey
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict

class PushkeyHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        uid      = self.get_argument('id', '')
        pushkey  = self.get_argument('pushkey', '')

        try:
            session = Session()
            count = session.query(UserPushKey).filter(UserPushKey.user_id == uid).count()

            if count == 0: # insert
                new_user_pushkey = UserPushKey(user_id=uid, pushkey = pushkey)
                session.add(new_user_pushkey)
            else: # update                
                row = session.query(UserPushKey).filter(UserPushKey.user_id == uid).one()
                row.pushkey = pushkey

            session.commit()

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

            print uid, 'modified pushkey successfully'

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
            
        finally:
            session.close()
            self.write(json.dumps(ret))
        