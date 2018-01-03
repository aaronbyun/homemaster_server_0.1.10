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
from sqlalchemy import and_, desc, func
from data.session.mysql_session import engine, Session
from data.model.data_model import UserReason, User, Booking
from data.dao.userdao import UserDAO
from data.encryption import aes_helper as aes
from response import Response
from response import add_err_message_to_response
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from err.error_handler import print_err_detail, err_dict
from utils.datetime_utils import convert_datetime_format2

# /user_in_funnel
class UserInFunnelHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        datetime = self.get_argument('datetime', '')
        datetime = dt.datetime.strptime(datetime, '%Y%m%d')

        ret = {}

        try:
            session = Session()

            userdao = UserDAO()
            users_register = userdao.get_users_who_register_only(datetime)
            users_address = userdao.get_users_who_add_address_only(datetime)

            user_groups = [users_register, users_address]
            for user_group in user_groups:
                for user in user_group:
                    if 'sigungu_id' in user:
                        del user['sigungu_id']
                    try:
                        user_id = user['id']
                        row = session.query(UserReason) \
                                    .filter(UserReason.user_id == user_id) \
                                    .one()

                        user['contact1']       = row.contact1
                        user['contact2']       = row.contact2
                        user['contact3']       = row.contact3
                        user['contact1_time']  = convert_datetime_format2(row.contact1_time) if row.contact1_time != None else ''
                        user['contact2_time']  = convert_datetime_format2(row.contact2_time) if row.contact2_time != None else ''
                        user['contact3_time']  = convert_datetime_format2(row.contact3_time) if row.contact3_time != None else ''
                        user['reason']         = row.reason
                        user['status']         = row.status
                        user['possible']       = row.possible

                    except Exception, e:
                        #print_err_detail(e)
                        user['contact1']       = ''
                        user['contact2']       = ''
                        user['contact3']       = ''
                        user['contact1_time']  = ''
                        user['contact2_time']  = ''
                        user['contact3_time']  = ''
                        user['reason']         = ''
                        user['status']         = ''
                        user['possible']       = ''


            result = session.query(UserReason, User, Booking) \
                            .join(User, UserReason.user_id == User.id) \
                            .join(Booking, User.id == Booking.user_id) \
                            .filter(UserReason.status == '성공') \
                            .group_by(User.id) \
                            .all()

            users_success = []
            for row in result:
                key = userdao.get_user_salt_by_id(row.User.id)[:16]
                crypto = aes.MyCrypto(key)

                user_name = crypto.decodeAES(row.User.name)
                user_phone = crypto.decodeAES(row.User.phone)

                booking_id = row.Booking.id

                users_success.append({'name' : user_name, \
                                    'phone' : user_phone, \
                                    'booking_id' : booking_id
                                    })

            user_in_funnel = {}
            user_in_funnel['register'] = users_register
            user_in_funnel['address']  = users_address
            user_in_funnel['success']  = users_success

            ret['response'] = user_in_funnel

            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))
