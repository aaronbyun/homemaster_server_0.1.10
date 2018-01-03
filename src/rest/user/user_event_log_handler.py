#-*- coding: utf-8 -*-

import sys

reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import json
import tornado.ioloop
import tornado.web
import datetime as dt
from utils.extract_aptcode import extract
from pymongo import MongoClient
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from logger.mongo_logger import get_mongo_logger
from pymongo import ASCENDING, DESCENDING

try:
    from utils.secrets import MONGO_USER, MONGO_PWD
except ImportError:
    MONGO_HOST = ''
    DB_PORT = ''



event_kor_dict = {}
event_kor_dict['register']                      = '회원가입'
event_kor_dict['login']                         = '로그인'
event_kor_dict['got userinfo']                  = '사용자 정보 확인'
event_kor_dict['check unpaid booking']          = '미납금 확인'
event_kor_dict['request available schedule']    = '가능 스케쥴 확인'
event_kor_dict['select schedule']               = '스케쥴 선택'
event_kor_dict['request user coupon']           = '쿠폰 조회'
event_kor_dict['user charge failure']           = '결제 실패'
event_kor_dict['register card']                 = '카드 등록'
event_kor_dict['add address']                   = '주소 추가'
event_kor_dict['confirm booking']               = '예약 확정'
event_kor_dict['add extra']                     = '추가 사항 입력'
event_kor_dict['got booking detail']            = '예약 정보 확인'


class UserEventLogHandler(tornado.web.RequestHandler):
    def initialize(self, mongo):
        self.mongo = mongo
        db = mongo.logs
        db.authenticate(MONGO_USER, MONGO_PWD, source = 'logs')
        self.col = db.logs

    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        user_id = self.get_argument('user_id', '')

        mongo_logger = get_mongo_logger()
        ret = {}

        try:
            query = {}
            query['user_id'] = user_id
            docs = self.col.find(query).sort('timestamp', DESCENDING)

            logs = []
            for doc in docs:
                log = {}
                log['user_id']      = doc['user_id']
                log['message']      = event_kor_dict[doc['message']] if doc['message'] in event_kor_dict else doc['message']
                log['level']        = doc['level']

                if 'log_time' in doc:
                    log['log_time']     = doc['log_time'].strftime('%Y-%m-%d %H:%M')
                else:
                    log['log_time'] = (doc['timestamp'].as_datetime() + dt.timedelta(hours = 9)) \
                                            .strftime('%Y-%m-%d %H:%M')

                logs.append(log)

            ret['response'] = logs
            self.set_status(Response.RESULT_OK)

            #mongo_logger.debug('user log', extra = {'log_time' : dt.datetime.now(), 'user_id' : user_id})

        except Exception, e:
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)
            #mongo_logger.error('failed user log', extra = {'err' : str(e)})
        finally:
            self.write(json.dumps(ret))
