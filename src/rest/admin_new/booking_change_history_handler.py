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
from bson.timestamp import Timestamp
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking
from data.dao.masterdao import MasterDAO
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.encryption import aes_helper as aes
from utils.datetime_utils import convert_datetime_format2

try:
    from utils.secrets import MONGO_USER, MONGO_PWD
except ImportError:
    MONGO_HOST = ''
    DB_PORT = ''

class BookingChangeHistoryHandler(tornado.web.RequestHandler):
    def initialize(self, mongo):
        self.mongo  = mongo

        print MONGO_USER, MONGO_PWD

        logs = mongo.logs
        logs.authenticate(MONGO_USER, MONGO_PWD, source = 'logs')

        self.db     = logs.logs

    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        booking_id = self.get_argument('booking_id', '')

        ret = {}

        try:
            # retrieve update logs from mongo
            '''{ "_id" : ObjectId("574436f28a34832173d79a74"),
            "timestamp" : Timestamp(1464088306, 392),
            "module" : "update_schedule_handler",
            "fileName" : "/home/dev/webapps/src/rest/booking/update_schedule_handler.py",
            "apply_to_all_behind" : 0,
             "lineNumber" : 181,
             "message" : "update logs",
             "user_id" : "cef0e0ef-b6b9-44c1-bd99-f59a844e51e1",
             "org_time" : "2016년 06월 17일 금요일 오전 11시",
             "thread" : NumberLong("140546989348672"),
             "level" : "DEBUG",
             "threadName" : "MainThread",
             "loggerName" : "hm_logger",
             "org_master_id" : "bd1bae4b-3b1b-41e1-8c23-703226457a19",
             "booking_id" : "GdB6wdQJ37m8LgkD",
             "changed_master_id" : "d0060b43-d1e4-4b48-aa53-b6817913275d",
             "changed_time" : "2016년 06월 19일 일요일 오전 11시",
             "method" : "post" }'''
            masterdao = MasterDAO()

            update_records = []
            cursor = self.db.find({'message' : 'update logs', 'booking_id' : booking_id}).sort('timestamp', 1)

            for item in cursor:
                org_master_id     = item['org_master_id']
                changed_master_id = item['changed_master_id']

                org_master_name = masterdao.get_master_name(org_master_id)
                changed_master_name = masterdao.get_master_name(changed_master_id)

                locale_time = item['timestamp'].as_datetime() + dt.timedelta(hours=9)

                logging_time = convert_datetime_format2(locale_time)

                by_whom = '없음'
                if 'by_manager' in item:
                    if item['by_manager'] == 1:
                        by_whom = '매니저'
                    else:
                        by_whom = '고객'

                org_time = item['org_time'] if 'org_time' in item else ''
                changed_time = item['changed_time'] if 'changed_time' in item else ''

                update_records.append({'org_time' : org_time,
                                        'changed_time' : changed_time,
                                        'org_master_name' : org_master_name,
                                        'changed_master_name' : changed_master_name,
                                        'logging_time' : logging_time,
                                        'by_whom' : by_whom})

            ret['response'] = {'update_records' : update_records}
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            self.write(json.dumps(ret))
