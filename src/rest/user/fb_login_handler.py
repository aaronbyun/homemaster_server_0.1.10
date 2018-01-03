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
from response import Response
from response import add_err_message_to_response
from data.session.mysql_session import engine, Session
from data.model.data_model import User
from err.error_handler import print_err_detail, err_dict
from sqlalchemy import and_
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel

class FBLoginHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        email       = self.get_argument('email', '')


        mongo_logger = get_mongo_logger()
        mix = get_mixpanel()

        try:
            session = Session()

            try:
                row = session.query(User).filter(User.email == email, User.active == 1).one()
            except NoResultFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_login_no_record'])
                mongo_logger.error('%s failed to logined' % email, extra = {'err' : str(e)})
                return

            except MultipleResultsFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_multiple_record'])
                mongo_logger.error('%s failed to logined' % email, extra = {'err' : str(e)})
                return

            try:
                row = session.query(User).filter(and_(User.email == email, User.authsource == 'FB', User.active == 1)).one()

            except NoResultFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_login_no_match'])
                mongo_logger.error('%s failed to logined' % email, extra = {'err' : str(e)})
                return

            except MultipleResultsFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_multiple_record'])
                mongo_logger.error('%s failed to logined' % email, extra = {'err' : str(e)})
                return


            guid = row.id
            name = row.name

            row.dateoflastlogin = dt.datetime.now()
            session.commit()

            print guid, ' has successfully log-ined! by fb at ', row.dateoflastlogin
            mix.track(guid, 'login', {'time' : dt.datetime.now()})
            mongo_logger.debug('%s logined' % email, extra = {'user_id' : guid, 'source' : 'Facebook'})

            ret['response'] = {'guid' : guid}
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
            mongo_logger.error('%s failed to logined' % email, extra = {'err' : str(e)})

        finally:
            session.close()

            self.write(json.dumps(ret))
