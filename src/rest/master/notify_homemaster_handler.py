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
import rest.booking.booking_constant as BC
from sqlalchemy import func
from data.session.mysql_session import engine, Session
from data.model.data_model import Master, MasterPushKey, MasterTimeSlot
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from cron.master_schedule_date_builder import ScheduleBuilder
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sender.push_sender import send_homemaster_notification

class NotifyHomemasterHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        title = self.get_argument('title', '알려드립니다.')
        content = self.get_argument('content', '홈마스터님 공지사항을 확인해주세요^^')

        try:
            ret = {}
            session = Session()
            result = session.query(Master, MasterTimeSlot, MasterPushKey) \
                            .join(MasterTimeSlot, Master.id == MasterTimeSlot.master_id) \
                            .join(MasterPushKey, Master.id == MasterPushKey.master_id) \
                            .filter(Master.active == 1) \
                            .all()

            # for test purpoese of server
            '''result = session.query(Master, MasterPushKey) \
                            .join(MasterPushKey, Master.id == MasterPushKey.master_id) \
                            .filter(Master.id == '336c6743-0601-4bcc-97f5-a2c23567a4dc') \
                            .all()'''

            for row in result:
                name = row.Master.name
                push_key = row.MasterPushKey.pushkey

                send_homemaster_notification([push_key], title, content)

            ret['response'] = Response.SUCCESS

            print 'notification was successfully called...'

            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()
            self.write(json.dumps(ret))
