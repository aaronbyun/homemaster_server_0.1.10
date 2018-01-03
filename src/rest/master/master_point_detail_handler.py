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
from data.model.data_model import MasterPoint, MasterPointDescription
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import func, Date, cast, or_, and_, desc

class MasterPointDetailHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")

        master_id = self.get_argument('master_id', '')

        ret = {}

        try:
            session = Session()

            detail_points = []

            result = session.query(MasterPoint, MasterPointDescription) \
                        .join(MasterPointDescription, MasterPoint.point_index == MasterPointDescription.index) \
                        .filter(MasterPoint.master_id == master_id) \
                        .order_by(desc(MasterPoint.point_date)) \
                        .all()

            for row in result:
                detail_points.append({'description' : row.MasterPointDescription.description, 'point' : row.MasterPoint.point, 'date' : dt.datetime.strftime(row.MasterPoint.point_date, '%Y-%m-%d %H:%M')})

            ret['response'] = detail_points
            self.set_status(Response.RESULT_OK)
            
        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()
            self.write(json.dumps(ret))