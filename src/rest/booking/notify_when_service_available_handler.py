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
from pymongo import MongoClient
from data.session.mysql_session import engine, Session
from data.dao.userdao import UserDAO
from data.encryption import aes_helper as aes
from data.model.data_model import Promotion, User, WaitingUser
from err.error_handler import print_err_detail, err_dict
from response import Response
from response import add_err_message_to_response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sender.sms_sender import send_promotion_code
from data.mixpanel.mixpanel_helper import get_mixpanel

try:
    from utils.secrets import MONGO_HOST, MONGO_PORT, MONGO_USER, MONGO_PWD
except ImportError:
    MONGO_HOST = 'localhost'
    DB_PORT = 27017
    MONGO_USER = ''
    MONGO_PWD = ''


class NotifyServiceAvailabilityHandler(tornado.web.RequestHandler):
    def post(self):
            self.set_header("Content-Type", "application/json")

            uid = self.get_argument('uid', '')
            sido = self.get_argument('sido', '')
            sigungu = self.get_argument('sigungu', '')

            print uid, sido, sigungu

            ret = {}

            UNUSED      = 0
            USED        = 1
            OCCUPIED    = 2

            mix = get_mixpanel()

            try:
                session = Session()
                row = session.query(Promotion).filter(Promotion.used == UNUSED).first()

                if row == None:
                    session.rollback()
                    add_err_message_to_response(ret, err_dict['err_no_promotion_codes'])
                    self.set_status(Response.RESULT_SERVERERROR)
                    print_err_detail(e)
                    return

                promotion_code = row.promotion_code

                row.used = OCCUPIED
                session.commit()

                # send text message to unavailable area
                try:
                    user_row = session.query(User).filter(User.id == uid).one()
                except NoResultFound, e:
                    session.close()
                    self.set_status(Response.RESULT_OK)
                    print_err_detail(e)
                    add_err_message_to_response(ret, err_dict['err_no_record'])
                    self.write(json.dumps(ret))
                    return

                except MultipleResultsFound, e:
                    session.close()
                    self.set_status(Response.RESULT_OK)
                    print_err_detail(e)
                    add_err_message_to_response(ret, err_dict['err_multiple_record'])
                    self.write(json.dumps(ret))
                    return

                userdao = UserDAO()

                key = userdao.get_user_salt_by_id(user_row.id)[:16]
                crypto = aes.MyCrypto(key)

                user_phone = crypto.decodeAES(user_row.phone)
                print user_phone
                print promotion_code


                #################################
                ###### add to waiting list ######
                #################################

                mongo = MongoClient(MONGO_HOST, MONGO_PORT)

                location = mongo.location
                location.authenticate(MONGO_USER, MONGO_PWD, source = 'location')

                db = location.address

                state_cursor = db.find_one({'level' : 'state', 'name' : sido})
                city_cursor = db.find_one({'level' : 'city', 'name' : sigungu})

                if state_cursor != None and city_cursor != None:
                    print 'cursor'
                    sido_id = state_cursor['code']
                    sigungu_id = city_cursor['code']

                    count = session.query(WaitingUser).filter(WaitingUser.user_id == uid).count()
                    if count == 0:
                        print 'sorry not available area...'
                        waiting_user = WaitingUser(user_id = uid, sido_id = sido_id, sigungu_id = sigungu_id)
                        session.add(waiting_user)

                        session.commit()
                        ret['response'] = Response.SUCCESS
                        self.set_status(Response.RESULT_OK)

                        print send_promotion_code(user_phone, promotion_code)

                        mix.track(uid, 'got coupon code', {'time' : dt.datetime.now(), 'sido' : sido, 'sigungu' : sigungu})
                    else: # code was already issued
                        add_err_message_to_response(ret, err_dict['err_code_already_issued'])
                        self.set_status(Response.RESULT_OK)

                else:
                    add_err_message_to_response(ret, err_dict['err_searching_address'])
                    self.set_status(Response.RESULT_OK)

            except Exception, e:
                session.rollback()
                add_err_message_to_response(ret, err_dict['err_mysql'])
                self.set_status(Response.RESULT_SERVERERROR)
                print_err_detail(e)

            finally:
                session.close()
                self.write(json.dumps(ret))
