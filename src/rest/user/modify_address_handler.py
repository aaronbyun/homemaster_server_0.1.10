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
from data.model.data_model import UserAddress, UserDefaultAddress
from utils.geo_utils import get_latlng_from_address, get_geohash
from data.encryption import aes_helper as aes
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import and_


class ModifyAddressHandler(tornado.web.RequestHandler):
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

            default_addr_index = userdao.get_user_default_address_index(guid)

            try:
                row = session.query(UserAddress) \
                            .filter(and_(UserAddress.user_id == guid, UserAddress.user_addr_index == default_addr_index)) \
                            .one()
            except NoResultFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_no_record'])
                mongo_logger.error('%s failed to find address, no record' % email, extra = {'err' : str(e)})
                return

            except MultipleResultsFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_multiple_record'])
                mongo_logger.error('%s failed to find address, multiple record' % email, extra = {'err' : str(e)})
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

            key = userdao.get_user_salt_by_id(guid)[:16]
            crypto = aes.MyCrypto(key)

            encrypted_address = crypto.encodeAES(str(address))

            row.address = encrypted_address
            row.size = size
            row.kind = kind
            row.latitude = latitude
            row.longitude = longitude
            row.geohash5 = geohash5
            row.geohash6 = geohash6

            session.commit()


            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

            print guid, 'add address successfully!'
            mix.track(guid, 'modify address', {'time' : dt.datetime.now()})
            mongo_logger.debug('%s modify address' % guid, extra = {'user_id' : guid, 'address' : address, 'size' : size, 'kind' : kind})

        except Exception, e:
            session.rollback()
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)
            mongo_logger.error('%s failed to modify address' % guid, extra = {'user_id' : guid, 'address' : address, 'size' : size, 'kind' : kind, 'err' : str(e)})
        finally:
            session.close()

            self.write(json.dumps(ret))
            return
