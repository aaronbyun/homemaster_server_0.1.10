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
import requests
from bson.timestamp import Timestamp
from data.session.mysql_session import engine, Session
from data.model.data_model import MasterDayoffRequest, Booking, Master, MasterScheduleByDate
from data.dao.masterdao import MasterDAO
from data.intermediate.value_holder import IntermediateValueHolder
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.encryption import aes_helper as aes
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from utils.datetime_utils import convert_datetime_format2
from logger.mongo_logger import get_mongo_logger
from sender.jandi_sender import send_jandi

class MasterDayoffRequestHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        master_id   = self.get_argument('master_id', '')
        off_date    = self.get_argument('off_date', '') # 20160603
        debug       = self.get_argument('debug', 0) # debug = 1: true 0: false

        master_date_key = '{0}_{1}'.format(master_id, off_date)

        off_date = dt.datetime.strptime(off_date, '%Y%m%d')

        ret = {}
        mongo_logger = get_mongo_logger()

        try:
            print "day off request ------------------------------------------- start"
            holder      = IntermediateValueHolder()
            session     = Session()
            masterdao = MasterDAO()

            # check redis that the master is not held
            is_held = holder.exists(master_date_key)
            print is_held
            if is_held:
                self.set_status(Response.RESULT_OK)
                mongo_logger.debug('doing booking', extra = {'master_id' : master_id, 'off_date' : off_date })
                add_err_ko_message_to_response(ret, '현재 예약이 진행 중 이라 휴무 신청이 불가능 합니다.')
                return

            # add request logs
            # type : 1 - request, 0 - cancel
            day_off_request = MasterDayoffRequest(master_id = master_id, date = off_date,
                                                 type = 1, request_time = dt.datetime.now())
            session.add(day_off_request)

            # master schedules by date active -> 0
            row = session.query(MasterScheduleByDate) \
                    .filter(MasterScheduleByDate.master_id == master_id) \
                    .filter(MasterScheduleByDate.date == off_date) \
                    .one()

            row.active = 0

            mongo_logger.debug('set row.active = 0', extra = {'master_id' : master_id, 'off_date' : off_date })

            # commit
            session.commit()

            mongo_logger.debug('session.commit()', extra = {'master_id' : master_id, 'off_date' : off_date })

            if debug == 0:
                master_name = masterdao.get_master_name(master_id)
                send_jandi('HOMEMASTER_REST', "휴무 신청", master_name + ' 홈마스터님 휴무 신청', '휴무날짜 : {}'.format(off_date))


            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

            print 'master_id', master_id, 'request dayoff request', off_date
            print "day off request ------------------------------------------- end"

        except NoResultFound, e:
            self.set_status(Response.RESULT_OK)
            mongo_logger.debug('no result', extra = {'master_id' : master_id, 'off_date' : off_date })
            add_err_ko_message_to_response(ret, '휴무 신청 가능 날짜가 아닙니다.')
            return

        except MultipleResultsFound, e:
            self.set_status(Response.RESULT_OK)
            mongo_logger.debug('multiple result', extra = {'master_id' : master_id, 'off_date' : off_date })
            add_err_ko_message_to_response(ret, '휴무 신청 중 에러가 발생했습니다.')
            return

        except Exception, e:
            session.rollback()
            print_err_detail(e)
            mongo_logger.debug('exception rest off', extra = {'master_id' : master_id, 'off_date' : off_date })
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()
            self.write(json.dumps(ret))
