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
import requests
from response import Response
from response import add_err_message_to_response
from data.session.mysql_session import engine, Session
from data.model.data_model import User, Booking
from data.dao.userdao import UserDAO
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from data.encryption import aes_helper as aes
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel
from utils.datetime_utils import convert_datetime_format3

try:
    from utils.secrets import CPID, T_SERVICE_KEY, T_BETA_SERVER, PKG_MASTER
except ImportError:
    CPID = ''
    T_SERVICE_KEY = ''
    T_BETA_SERVER = ''
    PKG_MASTER = ''

class TAPIHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        booking_id = self.get_argument('booking_id', '')
        caller_mdn = self.get_argument('caller_mdn', '')
        callee_mdn = self.get_argument('callee_mdn', '')

        mongo_logger = get_mongo_logger()
        mix = get_mixpanel()

        try:
            session = Session()
            row = session.query(Booking).filter(Booking.id == booking_id).one()

            data = {}
            data_header = {}
            data_body = {}

            text = convert_datetime_format3(row.start_time)
            if row.cleaning_status == 0:
                text += ' 예정'

            # data header
            data_header['VERSION']      = '1.0.0'
            data_header['CALLER_ID']    = PKG_MASTER

            # data body
            data_body['SERVICE_KEY']    = T_SERVICE_KEY
            data_body['SERVICE_NAME']   = "홈마스터"
            data_body['CALLER_MDN']     = caller_mdn
            data_body['CALLEE_MDN']     = callee_mdn
            data_body['TITLE']          = '[홈마스터] 담당 홈마스터입니다'
            data_body['TEXT']           = text
            data_body['APP_URL']        = 'homemaster://HMBookingList'
            data_body['WEB_URL']        = 'https://homemaster.co.kr'
            data_body['REQUEST_TYPE']   = '1'
            data_body['API_TYPE']       = '1'

            # post data
            data['HEADER'] = data_header
            data['BODY'] = data_body

            http_headers = {'Content-Type' : 'application/json; charset=utf-8', 'CPID' : CPID}
            response = requests.post(T_BETA_SERVER, data=json.dumps(data), headers=http_headers)
            print response.text

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            self.write(json.dumps(ret))
