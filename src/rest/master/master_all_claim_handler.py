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
from sqlalchemy import desc
from response import Response
from response import add_err_message_to_response
from data.dao.userdao import UserDAO
from data.encryption import aes_helper as aes
from data.session.mysql_session import engine, Session
from data.model.data_model import Master, MasterClaim, User
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from utils.datetime_utils import convert_datetime_format2

# /all_master_claim
class MasterAllClaimHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        ret = {}

        try:
            userdao = UserDAO()

            session = Session()
            result = session.query(MasterClaim, Master, User) \
                            .join(Master, MasterClaim.master_id == Master.id) \
                            .join(User, MasterClaim.user_id == User.id) \
                            .order_by(desc(MasterClaim.register_time)) \
                            .all()

            claims = []
            for row in result:
                key = userdao.get_user_salt_by_id(row.User.id)[:16]
                crypto = aes.MyCrypto(key)

                claim = {}
                claim['user_name']      = crypto.decodeAES(row.User.name)
                claim['user_phone']     = crypto.decodeAES(row.User.phone)
                claim['master_name']    = row.Master.name
                claim['text']           = row.MasterClaim.claim_text
                claim['datetime']       = convert_datetime_format2(row.MasterClaim.register_time)

                claims.append(claim)

            ret['response'] = claims
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()
            self.write(json.dumps(ret))
