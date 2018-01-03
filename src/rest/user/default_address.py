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

from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.session.mysql_session import engine, Session
from data.model.data_model import UserAddress, UserDefaultAddress
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DefaultAddressHandler(tornado.web.RequestHandler):
    def post(self):
        ret = {}

        guid = self.get_argument('id', '')
        idx = self.get_argument('default_idx', '')

        self.set_header("Content-Type", "application/json")

        try:
            session = Session()

            try:
                record = session.query(UserDefaultAddress).filter(UserDefaultAddress.user_id == guid).one()

            except NoResultFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_login_no_match'])
                return                

            except MultipleResultsFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_multiple_record'])
                return   


            record.address_idx = idx

            print guid, 'changed default address to', idx

            session.commit()

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)

        finally:
            session.close()
            self.write(json.dumps(ret))
