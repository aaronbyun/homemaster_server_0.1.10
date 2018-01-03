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
from sqlalchemy import and_
from data.session.mysql_session import engine, Session
from data.model.data_model import Rating, Booking, Master
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from sqlalchemy import desc, func

class MasterAvgRatingHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        try:
            session = Session()

            master_avg_ratings = []

            result = session.query(Master.name, func.ifnull(Master.img_url, ''), (func.ifnull(func.avg(Rating.rate_clean), 0) + func.ifnull(func.avg(Rating.rate_master), 0)) / 2, Master.active ) \
                    .outerjoin(Rating, Master.id == Rating.master_id) \
                    .group_by(Master.id) \
                    .having(Master.active == 1) \
                    .all()

            for row in result:
                rating_info = {}
                rating_info['master_name'] = row[0]
                rating_info['master_img_url'] = row[1]
                rating_info['master_avg_rating'] = float(row[2])

                master_avg_ratings.append(rating_info)

            ret['response'] = master_avg_ratings
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))