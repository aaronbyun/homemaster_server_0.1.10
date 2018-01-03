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

class MasterPenaltyAccumulateHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        master_id = self.get_argument('master_id', '')

        ret = {}
        panalties = []

        mongo_logger = get_mongo_logger()
        try:
            now = dt.datetime.now()
            this_year = now.year
            this_month = now.month

            session = Session()
            result = session.query(MasterPenalty.category_idx, MasterPenalty.penalty_idx, func.count(MasterPenalty)) \
                            .filter(MasterPenalty.master_id == master_id) \
                            .filter(func.year(MasterPenalty.penalty_date) == this_year) \
                            .filter(func.month(MasterPenalty.penalty_date) == this_month) \
                            .group_by(MasterPenalty.category_idx, MasterPenalty.penalty_idx) \
                            .order_by(MasterPenalty.category_idx, MasterPenalty.penalty_idx) \
                            .all()

            for row in result:
                print row
                panalties.append({'master_id' : master_id,
                                 'category_idx' : row[0],
                                 'penalty_idx' : row[1],
                                 'monthly_count' : row[2]})

            mongo_logger.debug('get penalty accumulate', extra = {'master_id' : master_id})

            ret['response'] = panalties
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
            mongo_logger.error('get penalty accumulate error', extra = {'master_id' : master_id})

        finally:
            session.close()
            self.write(json.dumps(ret))
