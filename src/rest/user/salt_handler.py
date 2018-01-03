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
from sqlalchemy import func
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from err.error_handler import print_err_detail, err_dict
from response import Response
from response import add_err_message_to_response
from logger.mongo_logger import get_mongo_logger

class SaltHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        email = self.get_argument('email', '')

        ret = {}

        if email == '':
            self.set_status(Response.RESULT_BADREQUEST)
            add_err_message_to_response(ret, err_dict['invalid_param'])
            self.write(json.dumps(ret))
            return

        mongo_logger = get_mongo_logger()

        try:
            session = Session()

            try:
                row = session.query(User).filter(User.email == email).one()

            except NoResultFound, e:
                try:
                    if len(email) == 11 and email.startswith('010'):
                        row = session.query(User) \
                                    .filter(func.aes_decrypt(func.from_base64(User.phone), \
                                    func.substr(User.salt, 1, 16)) == email,  \
                                    User.active == 1) \
                                    .one()
                    else:
                        session.close()
                        self.set_status(Response.RESULT_OK)
                        add_err_message_to_response(ret, err_dict['err_salt_no_match'])
                        mongo_logger.error('failed to get salt', extra = {'err' : str(e)})
                        return

                except NoResultFound, e:
                    session.close()
                    self.set_status(Response.RESULT_OK)
                    add_err_message_to_response(ret, err_dict['err_salt_no_match'])
                    mongo_logger.error('failed to get salt', extra = {'err' : str(e)})
                    return

                except MultipleResultsFound, e:
                    session.close()
                    self.set_status(Response.RESULT_OK)
                    add_err_message_to_response(ret, err_dict['err_dup_phone2'])
                    mongo_logger.error('failed to get salt', extra = {'err' : str(e)})
                    return

            except MultipleResultsFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_multiple_record'])
                return

            salt = row.salt
            ret['response'] = {'salt' : salt}
            self.set_status(Response.RESULT_OK)

            print email, 'got salt successfully!'

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()

            self.write(json.dumps(ret))
