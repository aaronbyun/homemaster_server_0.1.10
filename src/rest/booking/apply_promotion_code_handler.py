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
from data.model.data_model import Promotion, EventPromotion
from err.error_handler import print_err_detail, err_dict
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
try:
    from utils.stipulation_text import PROMOTION_CODES
except ImportError:
    PROMOTION_CODES = ['']

class ApplyPromotionCodeHandler(tornado.web.RequestHandler):
    def post(self):
            self.set_header("Content-Type", "application/json")
            self.set_header('Access-Control-Allow-Origin', '*')

            ret = {}

            UNUSED      = 0
            USED        = 1
            OCCUPIED    = 2

            promotion_code  = self.get_argument('promotion_code', '')

            try:
                session = Session()

                if promotion_code in PROMOTION_CODES: # 특별 할인 코드
                    discount_price = 0
                    now = dt.datetime.now()

                    print promotion_code, now

                    event_row = session.query(EventPromotion).filter(EventPromotion.code == promotion_code).one()

                    if event_row.count <= 0:
                        self.set_status(Response.RESULT_OK)
                        add_err_ko_message_to_response(ret, '이벤트 할인코드가 전부 사용되었습니다.')
                        return
                    if now >= event_row.expires:
                        self.set_status(Response.RESULT_OK)
                        add_err_ko_message_to_response(ret, '이벤트 할인코드 사용기간이 만료되었습니다.')
                        return
                    else:
                        discount_price = event_row.amount
                        event_row.count -= 1

                    session.commit()
                    ret['response'] = {'discount_price' : discount_price}
                    return

                try:
                    row = session.query(Promotion).filter(Promotion.promotion_code == promotion_code).one()
                except NoResultFound, e:
                    session.close()
                    self.set_status(Response.RESULT_OK)
                    add_err_message_to_response(ret, err_dict['err_no_used_promotion'])
                    return

                except MultipleResultsFound, e:
                    session.close()
                    self.set_status(Response.RESULT_OK)
                    add_err_message_to_response(ret, err_dict['err_multiple_record'])
                    return

                if promotion_code == 'abc' or promotion_code == 'abd': # super code
                    discount_price = row.discount_price

                else:
                    if row.used == USED:
                        session.close()
                        self.set_status(Response.RESULT_OK)
                        add_err_message_to_response(ret, err_dict['err_promotion_code_occupied'])
                        return

                    elif row.used == OCCUPIED:
                        discount_price = row.discount_price
                    else:
                        discount_price = row.discount_price
                        row.used = OCCUPIED

                    session.commit()

                ret['response'] = {'discount_price' : discount_price}
                self.set_status(Response.RESULT_OK)

                print row.promotion_code, 'was applied..'
            except Exception, e:
                session.rollback()
                add_err_message_to_response(ret, err_dict['err_mysql'])
                self.set_status(Response.RESULT_SERVERERROR)
                print_err_detail(e)

            finally:
                session.close()
                self.write(json.dumps(ret))
