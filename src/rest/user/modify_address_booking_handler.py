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
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.dao.userdao import UserDAO
from data.session.mysql_session import engine, Session
from data.model.data_model import UserAddress, UserDefaultAddress, Booking
from utils.geo_utils import get_latlng_from_address, get_geohash
from data.encryption import aes_helper as aes
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import and_
from utils.time_price_info import get_time_price

# /modify_booking_address
class ModifyAddressBookingHandler(tornado.web.RequestHandler):
    def post(self):
        ret = {}

        user_id = self.get_argument('user_id', '')
        index   = self.get_argument('index', '')
        address = self.get_argument('address', '')
        size    = self.get_argument('size', 0)
        kind    = self.get_argument('kind', 1)

        index = int(index)
        size = int(size)
        kind = int(kind)

        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        mongo_logger = get_mongo_logger()
        mix = get_mixpanel()

        try:
            session = Session()
            userdao = UserDAO()

            try:
                row = session.query(UserAddress) \
                            .filter(and_(UserAddress.user_id == user_id, UserAddress.user_addr_index == index)) \
                            .one()
            except NoResultFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_no_record'])
                mongo_logger.error('failed to find address, no record', extra = {'err' : str(e)})
                return

            except MultipleResultsFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_multiple_record'])
                mongo_logger.error('failed to find address, multiple record', extra = {'err' : str(e)})
                return

            latlng = get_latlng_from_address(address)
            if len(latlng) > 1:
                latitude = latlng[0]
                longitude = latlng[1]

                geohash5 = get_geohash(latitude, longitude, 5)
                geohash6 = get_geohash(latitude, longitude, 6)
            else:
                latitude = 0.0
                longitude = 0.0
                geohash5 = ''
                geohash6 = ''

            key = userdao.get_user_salt_by_id(user_id)[:16]
            crypto = aes.MyCrypto(key)

            encrypted_address = crypto.encodeAES(str(address))

            row.address = encrypted_address
            row.size = size
            row.kind = kind
            row.latitude = latitude
            row.longitude = longitude
            row.geohash5 = geohash5
            row.geohash6 = geohash6

            # modify booking info time and price
            now = dt.datetime.now().date()

            result = session.query(Booking) \
                            .filter(Booking.user_id == user_id) \
                            .filter(Booking.addr_idx == index) \
                            .filter(Booking.start_time >= now) \
                            .all()

            i = 0
            for row in result:
                if i == 0:
                    appointment_type = row.appointment_type
                    _, time, price, first_time = get_time_price(appointment_type, kind, size)

                new_duration = time
                org_duration = row.cleaning_duration

                new_price = price
                org_price = row.price

                # fix time
                row.estimated_end_time += dt.timedelta(minutes = (new_duration - org_duration))
                row.end_time = row.estimated_end_time

                # fix price
                row.price_with_task += (new_price - org_price)
                row.price = new_price

                row.cleaning_duration = new_duration

                i += 1

            session.commit()

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

            print user_id, 'modify address successfully!'
            mix.track(user_id, 'modify address', {'time' : dt.datetime.now()})
            mongo_logger.debug('%s modify address' % user_id, extra = {'user_id' : user_id, 'address' : address, 'size' : size, 'kind' : kind})

        except Exception, e:
            session.rollback()
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)
            mongo_logger.error('%s failed to modify address' % user_id, extra = {'user_id' : user_id, 'address' : address, 'size' : size, 'kind' : kind, 'err' : str(e)})
        finally:
            session.close()
            self.write(json.dumps(ret))
            return
