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
import requests
import datetime as dt
import pytz
from data.session.mysql_session import engine, Session
from data.model.data_model import Promotion
from err.error_handler import print_err_detail, err_dict
from response import Response
from response import add_err_message_to_response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

class ManagePromotionCodeHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        ret = {}

        promotion_code  = self.get_argument('promotion_code', '')

        try:
            session = Session()

            codes = []
            result3000 = session.query(Promotion) \
                            .filter(Promotion.discount_price == 3000) \
                            .filter(Promotion.used == 0) \
                            .limit(100)

            result5000 = session.query(Promotion) \
                            .filter(Promotion.discount_price == 5000) \
                            .filter(Promotion.used == 0) \
                            .limit(100)

            result10000 = session.query(Promotion) \
                            .filter(Promotion.discount_price == 10000) \
                            .filter(Promotion.used == 0) \
                            .limit(100)

            result50 = session.query(Promotion) \
                            .filter(Promotion.discount_price == 50) \
                            .filter(Promotion.used == 0) \
                            .limit(100)

            result100 = session.query(Promotion) \
                            .filter(Promotion.discount_price == 100) \
                            .filter(Promotion.used == 0) \
                            .limit(100)

            for row in result3000:
                codes.append({'code' : row.promotion_code, 'used' : row.used, 'discount_price' : row.discount_price})

            for row in result5000:
                codes.append({'code' : row.promotion_code, 'used' : row.used, 'discount_price' : row.discount_price})

            for row in result10000:
                codes.append({'code' : row.promotion_code, 'used' : row.used, 'discount_price' : row.discount_price})

            for row in result50:
                codes.append({'code' : row.promotion_code, 'used' : row.used, 'discount_price' : row.discount_price})

            for row in result100:
                codes.append({'code' : row.promotion_code, 'used' : row.used, 'discount_price' : row.discount_price})

            ret['response'] = codes
            self.set_status(Response.RESULT_OK)

            print 'All promotion codes information were retrieved..'
        except Exception, e:
            session.rollback()
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)

        finally:
            session.close()
            self.write(json.dumps(ret))
