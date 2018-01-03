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
from data.model.data_model import Master, MasterPenalty
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import func, Date, cast, or_, and_, desc
from logger.mongo_logger import get_mongo_logger
from utils.datetime_utils import convert_datetime_format2

class MasterChargePenaltyHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        master_id       = self.get_argument('master_id', '')
        category_idx    = self.get_argument('category_idx', '')
        penalty_idx     = self.get_argument('penalty_idx', '')
        penalty     = self.get_argument('penalty', '')

        category_idx = int(category_idx)
        penalty_idx = int(penalty_idx)

        ret = {}

        mongo_logger = get_mongo_logger()
        try:
            session = Session()
            master_penalty = MasterPenalty(master_id = master_id, category_idx = category_idx, penalty_idx = penalty_idx, penalty = penalty, penalty_date = dt.datetime.now())
            session.add(master_penalty)

            session.commit()

            mongo_logger.debug('charge penalty', extra = {'master_id' : master_id, 'category_idx' : category_idx, 'penalty_idx' : penalty_idx, 'penalty' : penalty})

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
            mongo_logger.error('charge penalty error', extra = {'master_id' : master_id, 'category_idx' : category_idx, 'penalty_idx' : penalty_idx, 'penalty' : penalty})

        finally:
            session.close()
            self.write(json.dumps(ret))
