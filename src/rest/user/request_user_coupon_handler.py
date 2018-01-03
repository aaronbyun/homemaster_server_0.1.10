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

from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.dao.userdao import UserDAO
from data.dao.addressdao import AddressDAO
from data.session.mysql_session import engine, Session
from data.model.data_model import UserCoupon
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from utils.geo_utils import get_latlng_from_address, get_geohash
from data.encryption import aes_helper as aes
from sqlalchemy import and_, or_, func
from utils.datetime_utils import convert_datetime_format
from rest.booking import booking_constant as BC
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel

class RequestUserCouponHandler(tornado.web.RequestHandler):
    def get(self):

        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        ret = {}

        user_id              = self.get_argument('user_id', '')

        mongo_logger = get_mongo_logger()
        now = dt.datetime.now()

        try:
            session = Session()

            results = session.query(UserCoupon) \
                             .filter(UserCoupon.user_id == user_id) \
                             .filter(func.date(UserCoupon.expire_date) >= now.date()) \
                             .filter(UserCoupon.used == 0) \
                             .order_by(UserCoupon.expire_date) \
                             .all()

            print "request user coupon sql query"

            user_coupons = []

            for result in results:
                user_coupon = {}
                user_coupon['id']             = result.id
                user_coupon['issue_date']     = dt.datetime.strftime(result.issue_date, '%Y.%m.%d')
                user_coupon['expire_date']    = dt.datetime.strftime(result.expire_date, '%Y.%m.%d')
                user_coupon['discount_price'] = result.discount_price
                user_coupon['description']    = result.description
                user_coupon['title']          = result.title

                user_coupons.append(user_coupon)

            ret['response'] = user_coupons
            self.set_status(Response.RESULT_OK)

            mongo_logger.debug('request user coupon', extra = {'user_id' : user_id })

        except Exception, e:
            session.rollback()
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)
            mongo_logger.error('failed to request user coupon', extra = {'user_id' : user_id, 'err' : str(e)})
        finally:
            session.close()
            self.write(json.dumps(ret))
            return
