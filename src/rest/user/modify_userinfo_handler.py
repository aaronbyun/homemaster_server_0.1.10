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
from data.model.data_model import UserAddress, UserDefaultAddress, User
from utils.geo_utils import get_latlng_from_address, get_geohash
from data.encryption import aes_helper as aes
from logger.mongo_logger import get_mongo_logger
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from data.mixpanel.mixpanel_helper import get_mixpanel
from sqlalchemy import and_


class ModifyUserInfoHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')
        
        ret = {}

        user_id    = self.get_argument('user_id', '')
        email      = self.get_argument('email', '')
        name       = self.get_argument('name', '')
        phone      = self.get_argument('phone', '')
        devicetype = self.get_argument('devicetype', 'None')
        gender     = self.get_argument('gender', 0)
        birthdate  = self.get_argument('birthdate', '')

        self.set_header("Content-Type", "application/json")

        gender = int(gender)

        mongo_logger = get_mongo_logger()
        mix = get_mixpanel()

        try:
            session = Session()
            userdao = UserDAO()

            try:
                row = session.query(User) \
                            .filter(User.id == user_id) \
                            .one()
            except NoResultFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_no_record'])
                mongo_logger.error('%s failed to find user, no record' % user_id, extra = {'err' : str(e)})
                return

            except MultipleResultsFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_multiple_record'])
                mongo_logger.error('%s failed to find user, multiple record' % user_id, extra = {'err' : str(e)})
                return

            key = userdao.get_user_salt_by_id(user_id)[:16]
            crypto = aes.MyCrypto(key)

            encrypted_name  = crypto.encodeAES(str(name))
            encrypted_phone = crypto.encodeAES(str(phone))
            encrypted_birthdate = crypto.encodeAES(str(birthdate))

            row.name  = encrypted_name
            row.email = email
            row.phone = encrypted_phone
            row.gender = gender
            row.devicetype = devicetype
            row.dateofbirth = encrypted_birthdate
            session.commit()


            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

            print user_id, 'modify user info successfully!'
            mix.track(user_id, 'modify userinfo', {'time' : dt.datetime.now()})
            mongo_logger.debug('%s modify userinfo' % user_id, extra = {'user_id' : user_id})

        except Exception, e:
            session.rollback()
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)
            mongo_logger.error('%s failed to modify userinfo' % user_id, extra = {'user_id' : user_id, 'err' : str(e)})
        finally:
            session.close()

            self.write(json.dumps(ret))
            return
