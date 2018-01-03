#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')

import json
import tornado.ioloop
import tornado.web
import uuid
import hashlib
import base64
import datetime as dt
from data.session.mysql_session import engine, Session
from data.model.data_model import User
from err.error_handler import print_err_detail, err_dict
from response import Response
from response import add_err_message_to_response
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from data.encryption import aes_helper as aes
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel

class RegisterWebHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        ret = {}

        name         = self.get_argument('name', '')
        authsource   = self.get_argument('authsource', 'None')
        devicetype   = self.get_argument('devicetype', 'web')
        email        = self.get_argument('email', '')
        password     = self.get_argument('password', '')
        phone        = self.get_argument('phone', '')
        is_b2b       = self.get_argument('is_b2b', 0)

        phone  = phone.replace('-', '')
        phone  = phone.replace(' ', '')

        gender = 2 # neither male or female
        birthdate = ''
        is_b2b = int(is_b2b)

        err_msg = ''

        if name == '':
            err_msg = 'name is invalid'
        elif email == '':
            err_msg = 'email is invalid'
        elif password == '':
            err_msg = 'password is invalid'

        if err_msg != '': # invalid argument situation
            ret['response'] = err_msg
            self.set_status(Response.RESULT_BADREQUEST)
            add_err_message_to_response(ret, err_dict['invalid_param'])
            return

        mongo_logger = get_mongo_logger()
        mix = get_mixpanel()

        try:
            session = Session()

            guid = str(uuid.uuid4())
            registerdate = dt.datetime.now()
            registerdate_str = dt.datetime.strftime(registerdate, '%Y%m%d')

            count = session.query(User).filter(User.email == email, User.active == 1).count()
            if count > 0:
                session.close()

                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_dup_email'])
                mongo_logger.debug('%s is already existed' % email, extra = {'err' : 'duplicate email'})
                return

            # phone duplicacy check
            count = session.query(User) \
                            .filter(func.aes_decrypt(func.from_base64(User.phone), \
                            func.substr(User.salt, 1, 16)) == phone,  \
                            User.active == 1) \
                            .count()
            if count > 0:
                session.close()

                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_dup_phone'])
                mongo_logger.debug('phone already existed', extra = {'err' : 'duplicate phone'})
                return

            salt = uuid.uuid4().hex
            encrypted_password = hashlib.sha256(salt + password).hexdigest()

            key = salt[:16]
            print key

            crypto = aes.MyCrypto(key)

            encrypted_name = crypto.encodeAES(str(name))
            encrypted_phone = crypto.encodeAES(str(phone))
            encrypted_birthdate = crypto.encodeAES(str(birthdate))

            print encrypted_name, name
            print encrypted_phone, phone
            print encrypted_birthdate, birthdate


            new_user = User(id = guid, name = encrypted_name, gender = gender, authsource = authsource,
                    devicetype = devicetype, email = email, password = encrypted_password, salt = salt,
                    phone = encrypted_phone, dateofbirth = encrypted_birthdate,
                    dateofreg = registerdate, dateoflastlogin= registerdate, is_b2b = is_b2b)
            session.add(new_user)
            session.commit()

            ret['response'] = guid
            self.set_status(Response.RESULT_OK)

            print email, 'has successfully registered..!!'

            print dt.datetime.now()
            mix.track(guid, 'register', {'time' : dt.datetime.now()})
            mix.people_set(guid, {'$name' : name, '$email' : email, '$gender' : gender,
                                  '$authsource' : authsource, '$phone' : phone, '$devicetype' : devicetype,
                                  '$brithdate' : birthdate, '$registerdate' : registerdate_str,
                                  '$time' : dt.datetime.now()},
                                  {'$ip' : '121.134.224.40'})
            mongo_logger.debug('register', extra = {'log_time' : dt.datetime.now(), 'user_id': guid, 'user_name' : name, 'gender' : gender, 'authsource' : authsource, 'devicetype' : devicetype, 'email' : email, 'phone' : phone})


        except Exception, e:
            session.rollback()
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)
            mongo_logger.error('failed to register', extra = {'log_time' : dt.datetime.now(), 'user_name' : name, 'gender' : gender, 'authsource' : authsource, 'devicetype' : devicetype, 'email' : email, 'phone' : phone, 'err' : str(e)})

        finally:
            session.close()
            self.write(json.dumps(ret))
