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
from data.model.data_model import UserMemo
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from logger.mongo_logger import get_mongo_logger
from sender.sms_sender import send_memo_requested

class UserMemoHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        uid     = self.get_argument('user_id', '')
        memo    = self.get_argument('memo', '')

        mongo_logger = get_mongo_logger()

        try:
            session = Session()

            query = session.query(UserMemo).filter(UserMemo.user_id == uid)
            if query.count() == 0:
                memo = UserMemo(user_id = uid, memo = memo, requested_datetime = dt.datetime.now())
                session.add(memo)
            else:
                row = query.one()
                row.requested_datetime = dt.datetime.now()
                row.memo = memo
                
            session.commit()

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

            # notification to managers
            #send_memo_requested(uid)

            print uid, 'posted memo successfully'
            mongo_logger.debug('%s posted memo' % uid)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
            mongo_logger.error('%s failed to posted memo' % uid, extra = {'err' : str(e)})
        finally:
            session.close()
            self.write(json.dumps(ret))
        