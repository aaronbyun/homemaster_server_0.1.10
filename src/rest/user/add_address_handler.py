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
from data.dao.addressdao import AddressDAO
from data.session.mysql_session import engine, Session
from data.model.data_model import UserAddress, UserDefaultAddress
from utils.geo_utils import get_latlng_from_address, get_geohash
from data.encryption import aes_helper as aes
from logger.mongo_logger import get_mongo_logger
from sqlalchemy import desc
from data.mixpanel.mixpanel_helper import get_mixpanel

class AddAddressHandler(tornado.web.RequestHandler):
    def post(self):
        ret = {}

        guid    = self.get_argument('id', '')
        address = self.get_argument('address', '')
        size    = self.get_argument('size', 0)
        kind    = self.get_argument('kind', 1)

        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        mongo_logger = get_mongo_logger()
        mix = get_mixpanel()

        try:
            session = Session()
            userdao = UserDAO()
            addressdao = AddressDAO()

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

            key = userdao.get_user_salt_by_id(guid)[:16]
            crypto = aes.MyCrypto(key)

            encrypted_address = crypto.encodeAES(str(address))

            count = session.query(UserAddress).filter(UserAddress.user_id == guid).count()
            last_index = session.query(UserAddress).filter(UserAddress.user_id == guid).order_by(desc(UserAddress.user_addr_index)).first()

            index = 0
            if last_index != None:
                index = last_index.user_addr_index + 1

            new_address = UserAddress(user_id = guid, address = encrypted_address, size = size, kind = kind,
                                        user_addr_index = index, latitude = latitude, longitude = longitude,
                                        geohash5 = geohash5, geohash6 = geohash6)
            session.add(new_address)
            session.commit()

            # set default address index
            if count == 0:
                new_default_address = UserDefaultAddress(user_id=guid, address_idx=index)
                session.add(new_default_address)
            else:
                record = session.query(UserDefaultAddress).filter(UserDefaultAddress.user_id == guid).one()
                record.address_idx = index

            session.commit()

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

            print guid, 'add address successfully!'

            gu_name = addressdao.get_gu_name(address)

            mix.people_set(guid, {'address' : address, 'gu' : gu_name})
            mix.track(guid, 'add address', {'time' : dt.datetime.now(), 'address' : address})
            mongo_logger.debug('add address', extra = {'log_time' : dt.datetime.now(), 'user_id' : guid, 'address' : address, 'size' : size, 'kind' : kind})

        except Exception, e:
            session.rollback()
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)
            mongo_logger.error('failed to add address', extra = {'log_time' : dt.datetime.now(), 'user_id' : guid, 'address' : address, 'size' : size, 'kind' : kind, 'err' : str(e)})
        finally:
            session.close()

            self.write(json.dumps(ret))
            return
