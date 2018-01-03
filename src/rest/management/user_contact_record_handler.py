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
from data.model.data_model import UserReason
from data.dao.userdao import UserDAO
from data.encryption import aes_helper as aes
from response import Response
from response import add_err_message_to_response
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from err.error_handler import print_err_detail, err_dict

# /user_contact_reason
class UserContactRecordHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        user_id = self.get_argument('user_id', '')
        contact1 = self.get_argument('contact1', '')
        contact2 = self.get_argument('contact2', '')
        contact3 = self.get_argument('contact3', '')
        reason   = self.get_argument('reason', '')
        status   = self.get_argument('status', '')
        possible = self.get_argument('possible', '')

        ret = {}

        session = Session()
        try:
            contact1_time = None
            if contact1 != '':
                contact1_time = dt.datetime.now()

            contact2_time = None
            if contact2 != '':
                contact2_time = dt.datetime.now()

            contact3_time = None
            if contact3 != '':
                contact3_time = dt.datetime.now()

            query = session.query(UserReason) \
                            .filter(UserReason.user_id == user_id) \

            if query.count() <= 0:
                reason = UserReason(user_id = user_id,
                                    contact1 = contact1,
                                    contact2 = contact2,
                                    contact3 = contact3,
                                    contact1_time = contact1_time,
                                    contact2_time = contact2_time,
                                    contact3_time = contact3_time,
                                    reason = reason,
                                    status = status,
                                    possible = possible)
                session.add(reason)
            else:
                row = query.one()
                row.contact1 = contact1
                row.contact1_time = contact1_time
                row.contact2 = contact2
                row.contact2_time = contact2_time
                row.contact3 = contact3
                row.contact3_time = contact3_time

                row.reason   = reason
                row.status   = status
                row.possible = possible

            session.commit()

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))
