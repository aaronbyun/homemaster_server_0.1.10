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
from sqlalchemy import func
from data.session.mysql_session import engine, Session
from data.model.data_model import Manager
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict

class AllManagerInfoHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        try:
            session = Session()

            managers = []

            result = session.query(Manager).all()

            for row in result:
                manager_info = {}
                manager_info['id']    = row.id
                manager_info['name']  = row.name
                manager_info['phone'] = row.phone 

                managers.append(manager_info)

            ret['response'] = managers
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))