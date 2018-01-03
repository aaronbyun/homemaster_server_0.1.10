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
from rest.booking import booking_constant as BC
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel
from hashids import Hashids

class CreateUserCouponHandler(tornado.web.RequestHandler):
    def post(self):

        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        ret = {}

        user_id              = self.get_argument('user_id', '')
        discount_price       = self.get_argument('discount_price', 0)
        expire_date          = self.get_argument('expire_date', '')
        title                = self.get_argument('title', '홈마스터 할인쿠폰')
        description          = self.get_argument('description', '')

        print 'expire_date : ', expire_date

        expire_date          = dt.datetime.strptime(expire_date, '%Y%m%d%H%M')
        discount_price       = int(discount_price)

        mongo_logger = get_mongo_logger()

        try:
            session = Session()
            now = dt.datetime.now()
            hashids = Hashids(min_length = 8, salt = user_id)
            coupon_id = hashids.encode(int(dt.datetime.strftime(now, '%Y%m%d%H%M%S')))

            user_coupon = UserCoupon(id = coupon_id, user_id = user_id, discount_price = discount_price,
                                     expire_date = expire_date, title = title, description = description,
                                     issue_date = now)

            session.add(user_coupon)

            session.commit()

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

            mongo_logger.debug('create user coupon', extra = {'user_id' : user_id, 'discount_price' : discount_price, 'expire_date' : expire_date, 'issue_date' : now})

        except Exception, e:
            session.rollback()
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)
            mongo_logger.error('failed to create user coupon', extra = {'user_id' : user_id, 'discount_price' : discount_price, 'expire_date' : expire_date, 'issue_date' : now, 'err' : str(e)})
        finally:
            session.close()
            self.write(json.dumps(ret))
            return
