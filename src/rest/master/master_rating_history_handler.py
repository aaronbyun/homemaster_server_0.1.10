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
from sqlalchemy import and_, or_
from data.session.mysql_session import engine, Session
from data.model.data_model import Rating, Booking, User, Master
from data.dao.userdao import UserDAO
from data.dao.masterdao import MasterDAO
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.encryption import aes_helper as aes
from sqlalchemy import desc
from utils.datetime_utils import convert_time_format

class MasterRatingHistoryHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")

        master_id = self.get_argument('master_id', '')
        only_5    = self.get_argument('only_5', 1)
        only_5 = int(only_5)

        ret = {}

        try:
            session = Session()

            ratings = []

            userdao = UserDAO()
            masterdao = MasterDAO()

            result = session.query(Rating, Booking, User, Master) \
                            .join(Booking, Rating.booking_id == Booking.id) \
                            .join(Master, Rating.master_id == Master.id) \
                            .join(User, Booking.user_id == User.id) \
                            .filter(Master.id == master_id)

            if only_5 == 1:
                result = result.filter(and_(Rating.rate_clean == 5.0, Rating.rate_master == 5.0)) \

            result = result.order_by(desc(Booking.start_time)).all()

            for row in result:
                key = userdao.get_user_salt(row.User.email)[:16]
                crypto = aes.MyCrypto(key)

                rating = {}

                rating['user_name']             = crypto.decodeAES(row.User.name)
                rating['start_date']            = dt.datetime.strftime(row.Booking.start_time, '%Y-%m-%d')
                rating['rating_date']           = dt.datetime.strftime(row.Rating.review_time, '%Y-%m-%d %H:%M')
                rating['start_time']            = convert_time_format(row.Booking.start_time.time())
                rating['booking_id']            = row.Booking.id
                rating['clean_rating']          = float(row.Rating.rate_clean)
                rating['clean_review']          = row.Rating.review_clean
                rating['master_rating']         = float(row.Rating.rate_master)
                rating['master_review']         = row.Rating.review_master

                ratings.append(rating)

            cleaning_avg_rating, master_avg_rating = masterdao.get_master_rating(master_id)
            master_name = masterdao.get_master_name(master_id)

            ret['response'] = {'cleaning_avg_rating' : cleaning_avg_rating,
                                'master_avg_rating' : master_avg_rating,
                                'ratings' : ratings,
                                'master_id' : master_id,
                                'master_name' : master_name}

            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))
