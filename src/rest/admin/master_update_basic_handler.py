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
from data.model.data_model import Master, MasterTimeSlot
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict

class MasterUpdateBasicHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        master_id   = self.get_argument('master_id', '')
        name        = self.get_argument('name', '')
        age         = self.get_argument('age', '')
        gender      = self.get_argument('gender', 2)
        address     = self.get_argument('address', '')
        phone       = self.get_argument('phone', '')
        manager_id  = self.get_argument('manager_id', '')
        level       = self.get_argument('level', 0)
        cardinal    = self.get_argument('cardinal', 0)

        # convert date type
        age = int(age)
        gender = int(gender)
        level = int(level)
        cardinal = int(cardinal)

        ret = {}

        try:
            session = Session()

            try:
                row_master = session.query(Master).filter(Master.id == master_id).one()
            except NoResultFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_no_record'])
                return

            row_master.manager_id = manager_id
            row_master.name = name
            row_master.age = age
            row_master.gender = gender
            row_master.address = address
            row_master.phone = phone
            row_master.level = level
            row_master.cardinal = cardinal

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
