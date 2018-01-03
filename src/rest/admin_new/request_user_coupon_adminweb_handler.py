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
from data.model.data_model import UserCoupon, User
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from utils.geo_utils import get_latlng_from_address, get_geohash
from data.encryption import aes_helper as aes
from sqlalchemy import and_, or_, func
from utils.datetime_utils import convert_datetime_format
from rest.booking import booking_constant as BC
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel

class RequestUserCouponAdminWebHandler(tornado.web.RequestHandler):
    def get(self):

        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        ret = {}

        user_id              = self.get_argument('user_id', '')

        mongo_logger = get_mongo_logger()
        now = dt.datetime.now()

        try:
            session = Session()
            userdao = UserDAO()

            try:
                result = session.query(User) \
                                .filter(User.id == user_id) \
                                .one()

            except NoResultFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_ko_message_to_response(ret, '등록되지 않은 고객 입니다.')
                return

            key = userdao.get_user_salt(result.email)[:16]
            crypto = aes.MyCrypto(key)

            name = crypto.decodeAES(result.name)

            user_coupons = {}
            user_coupons['user_name'] = name

            results = session.query(UserCoupon) \
                             .filter(UserCoupon.user_id == user_id) \
                             .order_by(UserCoupon.expire_date) \
                             .all()

            print "request user coupon sql query for adminweb"

            coupons = []
            for result in results:
                user_coupon = {}
                user_coupon['issue_date']     = dt.datetime.strftime(result.issue_date, '%Y.%m.%d')
                user_coupon['expire_date']    = dt.datetime.strftime(result.expire_date, '%Y.%m.%d')
                user_coupon['discount_price'] = result.discount_price
                user_coupon['used']           = 1 if result.used == 1 else 0
                user_coupon['is_expired']     = 1 if result.expire_date.date() <= now.date() else 0
                user_coupon['title']          = result.title
                user_coupon['booking_id']     = '' if result.booking_id == None else result.booking_id

                coupons.append(user_coupon)

            user_coupons['coupons'] = coupons

            ret['response'] = user_coupons
            self.set_status(Response.RESULT_OK)

            mongo_logger.debug('request user coupon for adminweb', extra = {'user_id' : user_id })

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
