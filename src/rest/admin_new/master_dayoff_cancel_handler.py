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
from bson.timestamp import Timestamp
from data.session.mysql_session import engine, Session
from data.model.data_model import MasterDayoffRequest, Booking, Master, MasterScheduleByDate
from data.dao.masterdao import MasterDAO
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.encryption import aes_helper as aes
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from utils.datetime_utils import convert_datetime_format2
from sender.jandi_sender import send_jandi

class MasterDayoffCancelHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        master_id   = self.get_argument('master_id', '')
        off_date    = self.get_argument('off_date', '') # 20160603

        master_date_key = '{0}_{1}'.format(master_id, off_date)

        off_date = dt.datetime.strptime(off_date, '%Y%m%d')

        ret = {}

        try:
            session     = Session()
            masterdao = MasterDAO()

            # add request logs
            # type : 1 - request, 0 - cancel
            day_off_request = MasterDayoffRequest(master_id = master_id, date = off_date,
                                                 type = 0, request_time = dt.datetime.now())
            session.add(day_off_request)

            # master schedules by date active -> 0
            row = session.query(MasterScheduleByDate) \
                    .filter(MasterScheduleByDate.master_id == master_id) \
                    .filter(MasterScheduleByDate.date == off_date) \
                    .one()

            row.active = 1

            # commit
            session.commit()
            
            master_name = masterdao.get_master_name(master_id)
            send_jandi('HOMEMASTER_REST', "휴무 신청 취소", master_name + ' 홈마스터님 휴무 신청 취소', '휴무 취소 날짜 : {}'.format(off_date))

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

            print 'master_id', master_id, 'cancel dayoff request', off_date

        except NoResultFound, e:
            self.set_status(Response.RESULT_OK)
            add_err_ko_message_to_response(ret, '휴무 신청 취소 가능 날짜가 아닙니다.')
            return

        except MultipleResultsFound, e:
            self.set_status(Response.RESULT_OK)
            add_err_ko_message_to_response(ret, '휴무 신청 취소 중 에러가 발생했습니다.')
            return

        except Exception, e:
            session.rollback()
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()
            self.write(json.dumps(ret))
