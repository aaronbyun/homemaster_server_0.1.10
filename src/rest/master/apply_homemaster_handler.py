#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import json
import requests
import tornado.ioloop
import tornado.web
import uuid
import datetime as dt

from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.session.mysql_session import engine, Session
from data.model.data_model import UserAddress, UserDefaultAddress
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from utils.google_sheet import Google
from sender.jandi_sender import send_jandi

class ApplyHomemasterHandler(tornado.web.RequestHandler):
    def post(self):

        name        = self.get_argument('name', '')
        birth       = self.get_argument('birth', '')
        phone       = self.get_argument('phone', '')
        address     = self.get_argument('address', '')
        workingexp  = self.get_argument('workingexp', '')

        ret = {}

        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        try:
            send_jandi('APPLY_HOMEMASTER', "홈마스터 지원하기", '이름: {}, 번호: {}'.format(name, phone), '생년월일: {}, 사는곳: {}, 경력: {}'.format(birth, address, workingexp))

            # google docs
            row = []
            row.append(name)
            row.append(birth)
            row.append(phone)
            row.append(address)
            row.append(workingexp)
            row.append(dt.datetime.now())

            Google(row = row, key = '1Rg5TYqJnNGGRwNc7pNwpoWUAbeN6_EP1kz2CtSv4EXY')

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)

        finally:
            self.write(json.dumps(ret))
