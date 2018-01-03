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
from data.model.data_model import Rating, Booking, User, Master
from data.dao.userdao import UserDAO
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.encryption import aes_helper as aes
from sqlalchemy import desc

class AllRatingInfoHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        try:
            session = Session()

            ratings = []

            userdao = UserDAO()

            result = session.query(Rating, Booking, User, Master) \
                            .join(Booking, Rating.booking_id == Booking.id) \
                            .join(Master, Rating.master_id == Master.id) \
                            .join(User, Booking.user_id == User.id) \
                            .order_by(desc(Rating.review_time)) \
                            .all()

            for row in result:                
                key = userdao.get_user_salt(row.User.email)[:16]
                crypto = aes.MyCrypto(key)

                rating = {}

                rating['user_name']             = crypto.decodeAES(row.User.name)
                rating['master_name']           = row.Master.name
                rating['appointment_type']      = row.Booking.appointment_type
                rating['start_time']            = dt.datetime.strftime(row.Booking.start_time, '%Y-%m-%d %H:%M')
                rating['estimated_end_time']    = dt.datetime.strftime(row.Booking.estimated_end_time,  '%Y-%m-%d %H:%M')
                rating['end_time']              = dt.datetime.strftime(row.Booking.end_time, '%Y-%m-%d %H:%M')
                rating['clean_rating']          = float(row.Rating.rate_clean)
                rating['clean_review']          = row.Rating.review_clean
                rating['master_rating']         = float(row.Rating.rate_master)
                rating['master_review']         = row.Rating.review_master
                rating['review_time']           = dt.datetime.strftime(row.Rating.review_time, '%Y-%m-%d %H:%M')

                ratings.append(rating)

            ret['response'] = ratings
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))