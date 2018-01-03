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

class ManagerInfoHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")

        manager_id = self.get_argument('manager_id', '')

        ret = {}

        try:
            session = Session()

            manager_info = {}

            row = session.query(Manager).filter(Manager.id == manager_id).scalar()

            if row == None:
                session.close()
                add_err_message_to_response(ret, err_dict['err_no_entry_to_cancel'])
                self.write(json.dumps(ret)) 
                return  
                
            manager_info['id']    = row.id
            manager_info['name']  = row.name
            manager_info['phone'] = row.phone 

            ret['response'] = manager_info
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))