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
from data.model.data_model import Master
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class MasterLoginHandler(tornado.web.RequestHandler):

    def post(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        phone       = self.get_argument('phone', '')

        try:
            session = Session()

            try:
                row = session.query(Master).filter(Master.phone == phone).filter(Master.active == 1).one()

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

            # update
            master_id = row.id
            master_name = row.name
            pwd = row.password
            img_url = row.img_url

            #row.dateoflastlogin = pytz.timezone('Asia/Seoul').localize(dt.datetime.now())
            row.dateoflastlogin = dt.datetime.now()
            session.commit()

            print master_id, ' has successfully log-ined!'

            issetpwd = 1
            if pwd == None:
                issetpwd = 0

            ret['response'] = {'master_id' : master_id, 'master_name' : master_name, 'issetpwd' : issetpwd, 'img_url' : img_url}
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()
            self.write(json.dumps(ret))
