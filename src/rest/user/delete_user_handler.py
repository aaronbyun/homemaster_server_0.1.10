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
from data.session.mysql_session import engine, Session
from data.model.data_model import User
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from err.error_handler import print_err_detail, err_dict
from response import Response
from response import add_err_message_to_response

class DeleteUserHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        user_id = self.get_argument('user_id', '')

        ret = {}

        try:
            session = Session()

            try:
                row = session.query(User).filter(User.id == user_id).one()

            except NoResultFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_salt_no_match'])
                return

            except NoResultFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_multiple_record'])
                return

            row.active = 0
            session.commit()

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

            print user_id, 'was requested to delete'

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()

            self.write(json.dumps(ret))
