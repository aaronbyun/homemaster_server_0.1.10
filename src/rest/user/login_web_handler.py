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
import hashlib
import base64
import datetime as dt
import pytz
from response import Response
from response import add_err_message_to_response
from data.session.mysql_session import engine, Session
from data.model.data_model import User
from data.dao.userdao import UserDAO
from err.error_handler import print_err_detail, err_dict
from sqlalchemy import func
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from data.encryption import aes_helper as aes
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel


class LoginWebHandler(tornado.web.RequestHandler):

    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        ret = {}

        email       = self.get_argument('email', '')
        password         = self.get_argument('password', '')

        print 'login', email, password

        mongo_logger = get_mongo_logger()
        mix = get_mixpanel()

        try:
            session = Session()
            userdao = UserDAO()

            try:
                row = session.query(User).filter(User.email == email, User.active == 1).one()

                salt = row.salt
                encrypted_password = hashlib.sha256(salt + password).hexdigest()

                row = session.query(User).filter(User.email == email, User.password == encrypted_password, User.active == 1).one()

            except NoResultFound, e:
                try:
                    if len(email) == 11 and email.startswith('010'):
                        row = session.query(User) \
                                    .filter(func.aes_decrypt(func.from_base64(User.phone), \
                                    func.substr(User.salt, 1, 16)) == email,  \
                                    User.active == 1) \
                                    .one()

                        print row.email

                        salt = row.salt
                        encrypted_password = hashlib.sha256(salt + password).hexdigest()

                        print salt, encrypted_password

                        row = session.query(User) \
                                    .filter(func.aes_decrypt(func.from_base64(User.phone), \
                                    func.substr(User.salt, 1, 16)) == email,  \
                                    User.password == encrypted_password, \
                                    User.active == 1) \
                                    .one()
                    else:
                        session.close()
                        self.set_status(Response.RESULT_OK)
                        add_err_message_to_response(ret, err_dict['err_login_no_match'])
                        mongo_logger.error('%s failed to logined' % email, extra = {'err' : str(e)})
                        return

                except NoResultFound, e:
                    session.close()
                    self.set_status(Response.RESULT_OK)
                    add_err_message_to_response(ret, err_dict['err_login_no_match'])
                    mongo_logger.error('%s failed to logined' % email, extra = {'err' : str(e)})
                    return
                except MultipleResultsFound, e:
                    session.close()
                    self.set_status(Response.RESULT_OK)
                    add_err_message_to_response(ret, err_dict['err_dup_phone2'])
                    mongo_logger.error('%s failed to logined' % email, extra = {'err' : str(e)})
                    return

            except MultipleResultsFound, e:
                session.close()
                print_err_detail(e)
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_multiple_record'])
                mongo_logger.error('%s failed to logined' % email, extra = {'err' : str(e)})
                return

            # update
            guid = row.id
            name = row.name

            #row.dateoflastlogin = pytz.timezone('Asia/Seoul').localize(dt.datetime.now())
            row.dateoflastlogin = dt.datetime.now()
            session.commit()

            print guid, ' has successfully log-ined! at ', row.dateoflastlogin
            mix.track(guid, 'login', {'time' : dt.datetime.now()})
            mongo_logger.debug('login', extra = {'log_time' : dt.datetime.now(), 'user_id' : guid})

            ret['response'] = {'guid' : guid}
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
            mongo_logger.error('failed to logined', extra = {'log_time' : dt.datetime.now(), 'err' : str(e)})

        finally:
            session.close()
            self.write(json.dumps(ret))
