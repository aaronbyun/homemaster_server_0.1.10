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
from data.model.data_model import UserCoupon, Booking
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from utils.geo_utils import get_latlng_from_address, get_geohash
from data.encryption import aes_helper as aes
from sqlalchemy import and_, or_, func
from utils.datetime_utils import convert_datetime_format
from rest.booking import booking_constant as BC
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel

class ApplyUserCouponHandler(tornado.web.RequestHandler):
    def post(self):

        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        ret = {}

        user_id              = self.get_argument('user_id', '')
        booking_id           = self.get_argument('booking_id', '')
        coupon_id            = self.get_argument('coupon_id', '')

        mongo_logger = get_mongo_logger()
        now = dt.datetime.now()

        try:
            session = Session()

            count = session.query(UserCoupon) \
                           .filter(UserCoupon.booking_id == booking_id) \
                           .count()

            if count > 0:
                self.set_status(Response.RESULT_OK)
                add_err_ko_message_to_response(ret, '이미 쿠폰이 적용된 예약 입니다.')
                return


            row = session.query(UserCoupon) \
                         .filter(UserCoupon.user_id == user_id) \
                         .filter(UserCoupon.id == coupon_id) \
                         .one()

            if row.expire_date <= now:
                self.set_status(Response.RESULT_OK)
                add_err_ko_message_to_response(ret, '사용 기한이 만료된 쿠폰 입니다.')
                return

            if row.used != 0:
                self.set_status(Response.RESULT_OK)
                add_err_ko_message_to_response(ret, '이미 사용한 쿠폰 입니다.')
                return

            ret['response'] = row.discount_price
            self.set_status(Response.RESULT_OK)

            mongo_logger.debug('apply user coupon', extra = {'user_id' : user_id, 'booking_id' : booking_id })

        except Exception, e:
            session.rollback()
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)
            mongo_logger.error('failed to apply user coupon', extra = {'user_id' : user_id, 'booking_id' : booking_id, 'err' : str(e)})
        finally:
            session.close()
            self.write(json.dumps(ret))
            return
