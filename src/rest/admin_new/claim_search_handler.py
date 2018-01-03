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
from sqlalchemy import and_, or_, func
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, User, Master, UserClaim
from data.dao.userdao import UserDAO
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.encryption import aes_helper as aes
from sqlalchemy import desc

class ClaimSearchHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        ret = {}

        print "test-intro"

        try:
            session = Session()

            result = session.query(UserClaim, Booking, User, Master) \
                            .join(Booking, UserClaim.booking_id == Booking.id) \
                            .join(Master, Master.id == Booking.master_id) \
                            .join(User, User.id == Booking.user_id) \
                            .all()
            claims = []
            Userdao = UserDAO()

            print result

            for record in result:
                key = Userdao.get_user_salt(record.User.email)[:16]
                if key == None or key == '':
                    continue

                crypto = aes.MyCrypto(key)

                claim_info = {}
                claim_info['cleanning_date'] = dt.datetime.strftime(record.Booking.start_time, '%Y-%m-%d %H:%M')
                claim_info['user_name']      = crypto.decodeAES(record.User.name)
                claim_info['user_phone']     = crypto.decodeAES(record.User.phone)
                claim_info['master_name']    = record.Master.name
                claim_info['claim_comment']  = record.UserClaim.comment
                claim_info['claim_reg_time'] = dt.datetime.strftime(record.UserClaim.register_time, '%Y-%m-%d %H:%M')
                claims.append(claim_info)

            ret['response'] = claims;
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))
