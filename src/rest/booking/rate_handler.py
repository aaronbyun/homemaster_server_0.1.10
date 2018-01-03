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
from data.model.data_model import Rating, Booking, MasterPoint, MasterPointDescription, MasterPrize
from err.error_handler import print_err_detail, err_dict
from response import Response
from response import add_err_message_to_response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sender.sms_sender import send_rating_granted
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel
from sender.alimtalk_sender import send_alimtalk
from sender.jandi_sender import send_jandi
from data.dao.userdao import UserDAO
from data.dao.masterdao import MasterDAO

try:
    from utils.secrets import MANAGERS_CALL
except ImportError:
    MANAGERS_CALL = ''

class RatingHandler(tornado.web.RequestHandler):
    def post(self):
            self.set_header("Content-Type", "application/json")
            self.set_header('Access-Control-Allow-Origin', '*')

            ret = {}

            booking_id  = self.get_argument('booking_id', '')
            c_rate        = self.get_argument('clean_rate', 0.0)
            c_review_msg  = self.get_argument('clean_review', '')
            m_rate        = self.get_argument('master_rate', 0.0)
            m_review_msg  = self.get_argument('master_review', '')

            c_rate = float(c_rate)
            m_rate = float(m_rate)

            mongo_logger = get_mongo_logger()
            mix = get_mixpanel()

            try:
                session = Session()

                try:
                    row = session.query(Booking).filter(Booking.id == booking_id).one()

                except NoResultFound, e:
                    session.close()
                    self.set_status(Response.RESULT_OK)
                    add_err_message_to_response(ret, err_dict['err_no_record'])
                    return

                except MultipleResultsFound, e:
                    session.close()
                    self.set_status(Response.RESULT_OK)
                    add_err_message_to_response(ret, err_dict['err_multiple_record'])
                    return

                master_id = row.master_id
                user_id = row.user_id

                rating = Rating(booking_id = booking_id, master_id = master_id, rate_clean = c_rate, review_clean = c_review_msg,
                                rate_master = m_rate, review_master = m_review_msg, review_time = dt.datetime.now())

                session.add(rating)

                row.havereview = 1 # review flag update

                if c_rate + m_rate == 10:
                    master_id = row.master_id
                    # 평점 5점 이상 1점 획득
                    master_prize = MasterPrize(master_id = master_id, prize = 3000, prize_description = '평점 5점', earn_date = dt.datetime.now())
                    session.add(master_prize)

                session.commit()

                ret['response'] = Response.SUCCESS
                self.set_status(Response.RESULT_OK)

                mix.track(user_id, 'rated', {'time' : dt.datetime.now(), 'c_rate' : c_rate, 'm_rate' : m_rate, 'c_msg' : c_review_msg, 'm_msg' : m_review_msg})
                mongo_logger.debug('rated', extra = {'user_id' : user_id, 'c_rate' : c_rate, 'm_rate' : m_rate, 'c_msg' : c_review_msg, 'm_msg' : m_review_msg})

                #send_rating_granted(booking_id, c_rate, m_rate)

                userdao = UserDAO()
                masterdao = MasterDAO()

                user_name = userdao.get_user_name(user_id)
                master_name = masterdao.get_master_name(master_id)

                #for manager_phone in MANAGERS_CALL.split(','):
                #    send_alimtalk(manager_phone, 'noti_manager_rate', user_name, master_name, c_rate, m_rate)
                send_jandi('NEW_BOOKING', "평가 알림", user_name + ' 고객님,'  + master_name + '님 평가', '클리닝 평가 : {}, 마스터 평가 : {}\n클리닝 평가 내용 : {}\n\n, 마스터 평가 내용 : {}'.format(c_rate, m_rate, c_review_msg, m_review_msg))

                print booking_id, 'was successfully rated...'
            except Exception, e:
                session.rollback()
                add_err_message_to_response(ret, err_dict['err_mysql'])
                self.set_status(Response.RESULT_SERVERERROR)
                print_err_detail(e)

            finally:
                session.close()
                self.write(json.dumps(ret))
