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
from data.model.data_model import MasterMemo
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from logger.mongo_logger import get_mongo_logger

class MasterPostMemoHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        uid     = self.get_argument('user_id', '')
        mid     = self.get_argument('master_id', '')
        memo    = self.get_argument('memo', '')

        mongo_logger = get_mongo_logger()

        try:
            session = Session()

            memo = MasterMemo(user_id = uid, master_id = mid, memo = memo, datetime = dt.datetime.now())
            session.add(memo)
            session.commit()

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)


            print mid, 'posted memo successfully'
            mongo_logger.debug('%s posted memo' % mid)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
            mongo_logger.error('%s failed to posted memo' % mid, extra = {'err' : str(e)})
        finally:
            session.close()
            self.write(json.dumps(ret))
        