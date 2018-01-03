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
from data.dao.userdao import UserDAO
from err.error_handler import print_err_detail, err_dict
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from sqlalchemy import func, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from data.encryption import aes_helper as aes
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel

try:
    from utils.secrets import MONGO_USER, MONGO_PWD
except ImportError:
    MONGO_HOST = ''
    DB_PORT = ''

class RequestCleaningHandler(tornado.web.RequestHandler):
    def initialize(self, mongo):

        self.mongo = mongo
        booking = mongo.booking
        booking.authenticate(MONGO_USER, MONGO_PWD, source = 'booking')

        self.db = booking.customer

    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        dates       = self.get_argument('dates', '')
        time        = self.get_argument('time', '')
        period      = self.get_argument('period', '')
        tasks       = self.get_argument('tasks', '')

        total_duration    = self.get_argument('total_duration', 180)
        total_price       = self.get_argument('total_price', '')

        basic_duration    = self.get_argument('basic_duration', 180)
        basic_price       = self.get_argument('basic_price', '')

        dirty       = self.get_argument('dirty', 0)

        name        = self.get_argument('name', '')
        phone       = self.get_argument('phone', '')

        address     = self.get_argument('address', '')
        size        = self.get_argument('size', '')
        rooms       = self.get_argument('rooms', '')
        baths       = self.get_argument('baths', '')
        message     = self.get_argument('message', '')

        password    = self.get_argument('password', '')

        # convert parameters
        dates       = dates.split(',')

        start_date  = dates[0]

        if len(dates) > 1:
            dates       = dates[1:]

        total_duration    = int(total_duration)
        total_price       = int(total_price)

        basic_duration    = int(basic_duration)
        basic_price       = int(basic_price)

        rooms       = int(rooms)
        baths       = int(baths)
        size        = int(size)

        dirty       = int(dirty)
        if dirty == 1:
            dirty = '더러워요'
        else:
            dirty = '보통이에요'

        cleaning_id = str(uuid.uuid4())

        ret = {}

        userdao = UserDAO()
        mongo_logger = get_mongo_logger()

        try:
            # 전화번호나 이메일이 없는 경우에는 회원가입을 시키고 진행
            # 있는 경우에는 가입 시키지 않고 그대로 진행
            session = Session()
            user_query = session.query(User) \
                            .filter(func.aes_decrypt(func.from_base64(User.phone), \
                            func.substr(User.salt, 1, 16)) == phone,  \
                            User.active == 1) \

            if user_query.count() <= 0:
                user_id = str(uuid.uuid4())

                salt = uuid.uuid4().hex
                encrypted_password = hashlib.sha256(salt + password).hexdigest()

                key = salt[:16]
                crypto = aes.MyCrypto(key)

                encrypted_name = crypto.encodeAES(str(name))
                encrypted_phone = crypto.encodeAES(str(phone))

                email = '{}@webuser.co.kr'.format(phone)

                new_user = User(id = user_id, name = encrypted_name,
                                gender = 2, authsource = 'web',
                                devicetype = 'web', email = email,
                                password = encrypted_password, salt = salt,
                                phone = encrypted_phone,
                                dateofreg = dt.datetime.now(),
                                dateoflastlogin = dt.datetime.now())
                session.add(new_user)
                session.commit()
            else:
                user = user_query.order_by(desc(User.dateoflastlogin)).first()
                user_id = user.id
                email = user.email

            if user_id == None or user_id == '':
                self.set_status(Response.RESULT_OK)
                add_err_ko_message_to_response(ret, '잘못된 사용자 아이디 입니다.')
                return

            # size : 0, kind : 3
            # 일단 입력한 그대로 주소 추가. 주소 형식이 자유 형식이기 때문에
            # 관리자가 판단하여 주소를 수정하거나, 예약을 취소할 수 있음

            address_index = userdao.add_new_address(user_id, address, size, 3, rooms, baths)

            booking = {}
            booking['user_id']  = user_id
            booking['cleaning_id']  = cleaning_id
            booking['dates']    = dates
            booking['start_date']    = start_date
            booking['time']     = time
            booking['period']   = period
            booking['total_duration'] = total_duration
            booking['total_price']    = total_price
            booking['basic_duration'] = basic_duration
            booking['basic_price']    = basic_price
            booking['dirty']    = dirty
            booking['tasks']    = tasks
            booking['name']     = name
            booking['phone']    = phone
            booking['address']  = address
            booking['address_index']  = address_index
            booking['rooms']     = rooms
            booking['baths']     = baths
            booking['message']   = message
            booking['email']     = email
            booking['size']     = size
            booking['password']  = password
            booking['count']     = 0
            booking['booking_ids']  = []
            booking['request_time'] = dt.datetime.now()

            self.db.insert(booking)

            ret['response'] = cleaning_id
            self.set_status(Response.RESULT_OK)

            mongo_logger.debug('web request booking', extra = {'user_id': user_id,
                                                                'cleaning_id' : cleaning_id,
                                                                'dates' : dates,
                                                                'sel_time' : time,
                                                                'sel_period' : period,
                                                                'total_duration' : total_duration,
                                                                'toatl_price' : total_price,
                                                                'basic_duration' : basic_duration,
                                                                'basic_price' : basic_price,
                                                                'tasks' : tasks,
                                                                'rooms' : rooms,
                                                                'baths' : baths,
                                                                'user_name' : name,
                                                                'user_phone' : phone,
                                                                'user_address' : address})

        except Exception, e:
            session.rollback()
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)
            mongo_logger.error('failed to web request booking',
                                                  extra = {'user_id': user_id,
                                                          'cleaning_id' : cleaning_id,
                                                          'dates' : dates,
                                                          'sel_time' : time,
                                                          'sel_period' : period,
                                                          'total_duration' : total_duration,
                                                          'toatl_price' : total_price,
                                                          'basic_duration' : basic_duration,
                                                          'basic_price' : basic_price,
                                                          'tasks' : tasks,
                                                          'rooms' : rooms,
                                                          'baths' : baths,
                                                          'user_name' : name,
                                                          'user_phone' : phone,
                                                          'user_address' : address})

        finally:
            session.close()
            self.write(json.dumps(ret))
