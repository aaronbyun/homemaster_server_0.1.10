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
from data.model.data_model import Master, MasterPrize
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import func, Date, cast, or_, and_, desc
from logger.mongo_logger import get_mongo_logger

class MasterAddPrizeHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        master_id = self.get_argument('master_id', '')
        prize     = self.get_argument('prize', 0)
        prize_description = self.get_argument('prize_description', '')

        prize = int(prize)

        ret = {}

        mongo_logger = get_mongo_logger()

        try:
            session = Session()
            master_prize = MasterPrize(master_id = master_id, prize = prize, prize_description = prize_description, earn_date = dt.datetime.now())
            session.add(master_prize)

            session.commit()

            mongo_logger.debug('add point', extra = {'master_id' : master_id, 'prize' : prize, 'prize_description' : prize_description})

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
            mongo_logger.error('add point error', extra = {'master_id' : master_id, 'prize' : prize, 'prize_description' : prize_description})

        finally:
            session.close()
            self.write(json.dumps(ret))
