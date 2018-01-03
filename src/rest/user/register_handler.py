#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')

import json
import tornado.ioloop
import tornado.web
import uuid
import datetime as dt
from data.session.mysql_session import engine, Session
from data.model.data_model import User, UserCoupon, Promotion
from err.error_handler import print_err_detail, err_dict
from response import Response
from response import add_err_message_to_response
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from data.encryption import aes_helper as aes
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel
from hashids import Hashids
from sender.sms_sender import SMS_Sender

class RegisterHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        name         = self.get_argument('name', '')
        gender       = self.get_argument('gender', 1)
        authsource   = self.get_argument('authsource', 'None')
        devicetype   = self.get_argument('devicetype', 'None')
        email        = self.get_argument('email', '')
        password     = self.get_argument('password', '')
        salt         = self.get_argument('salt', '')
        phone        = self.get_argument('phone', '')
        birthdate    = self.get_argument('birthdate', '')
        registerdate = self.get_argument('regdate', '')

        if gender == '':
            gender = 1

        gender = int(gender)

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
            registerdate_str = registerdate
            #registerdate = dt.datetime.strptime(registerdate, '%Y-%m-%d').date()
            registerdate = dt.datetime.now()

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
                    devicetype = devicetype, email = email, password = password, salt = salt,
                    phone = encrypted_phone, dateofbirth = encrypted_birthdate,
                    dateofreg = registerdate, dateoflastlogin= registerdate)
            session.add(new_user)
            session.commit()

            now = dt.datetime.now()
            expire_date = dt.datetime(2016, 12, 31, 23, 59)

            if now <= expire_date:
                user_id = guid
                discount_price = 10000
                title           = '크리스마스는 깨끗한 집에서!'
                description     = '1만원 할인쿠폰'

                hashids = Hashids(min_length = 8, salt = user_id)
                coupon_id = hashids.encode(int(dt.datetime.strftime(now, '%Y%m%d%H%M%S')))

                user_coupon = UserCoupon(id = coupon_id, user_id = user_id, discount_price = discount_price,
                                     expire_date = expire_date, title = title, description = description,
                                     issue_date = now)

                session.add(user_coupon)
                session.commit()

                sender = SMS_Sender()

                if devicetype == 'ios':
                    # send lms
                    row = session.query(Promotion) \
                                .filter(Promotion.discount_price == 10000) \
                                .filter(Promotion.used == 0) \
                                .first()
                    code = row.promotion_code
                    row.used = 2
                    session.commit()

                    sender.send2(mtype = 'lms', to = phone, subject = '홈마스터 12월 회원가입 이벤트!',
                                text = '홈마스터 앱에서 클리닝 예약 시, 아래 코드를 입력 해주세요 (10,000원 할인코드): \n' + code)
                elif devicetype == 'android':
                    sender.send2(mtype = 'lms', to = phone, subject = '홈마스터 12월 회원가입 이벤트!',
                                text = '홈마스터 10,000 할인 쿠폰이 도착했습니다. 앱의 쿠폰함에서 확인해주세요~')

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
