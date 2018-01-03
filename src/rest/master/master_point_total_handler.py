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
from data.model.data_model import MasterPointDescription, MasterPoint, Master
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import func, desc


class MasterPointTotalHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        try:
            session = Session()

            master_points = []

            result = session.query(Master, MasterPoint, func.sum(MasterPoint.point)) \
                            .outerjoin(MasterPoint, MasterPoint.master_id == Master.id) \
                            .filter(Master.active == 1) \
                            .group_by(Master.id) \
                            .order_by(desc(MasterPoint.point_date)) \
                            .all()

            for row in result:
                master_point = {}

                master_point['point'] = 0
                if row.MasterPoint != None:
                    master_point['point'] = int(row[2])
                master_point['master_id'] = row.Master.id
                master_point['master_name'] = row.Master.name

                master_points.append(master_point)

            ret['response'] = master_points

            self.set_status(Response.RESULT_OK)
            
        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()
            self.write(json.dumps(ret))