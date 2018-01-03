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

class InqueryOfficeCleaningHandler(tornado.web.RequestHandler):
    def post(self):

        corp_name       = self.get_argument('corp_name', '')
        address         = self.get_argument('address', '')
        corp_type       = self.get_argument('corp_type', '')
        reserve_name    = self.get_argument('reserve_name', '')
        phone           = self.get_argument('phone', '')
        service_type    = self.get_argument('service_type', '')

        ret = {}

        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        try:
            send_jandi('OFFICE_CLEANING', "오피스 클리닝 문의", '{} 담당자 : {}'.format(corp_name, reserve_name), '폰 : {}, 주소 : {}'.format(phone, address))

            # google docs
            row = []
            row.append(corp_name)
            row.append(address)
            row.append(corp_type)
            row.append(reserve_name)
            row.append(phone)
            row.append('')
            row.append(service_type)
            row.append(dt.datetime.now())

            Google(row = row, key = '1nWE_GUviNB0huIYQQSwESEGOjrp_oGPJjOyqmpFCzmU')

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)

        finally:
            self.write(json.dumps(ret))
