#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import json
import requests
import tornado.ioloop
import tornado.web
import base64
import uuid
import hashlib
import requests
import xmltodict
import pickle
import datetime as dt
import booking.booking_constant as BC
from hashids import Hashids
from schedule.schedule_helper import HMScheduler
from nptime import nptime
from utils.datetime_utils import time_to_str, timedelta_to_time, time_to_minutes
from utils.geo_utils import get_moving_time
from data.session.mysql_session import engine, Session
from data.intermediate.value_holder import IntermediateValueHolder
from data.model.data_model import User, Order11st, Booking
from data.dao.userdao import UserDAO
from data.dao.addressdao import AddressDAO
from data.dao.masterdao import MasterDAO
from err.error_handler import print_err_detail, err_dict
from response import Response
from data.intermediate.value_holder import IntermediateValueHolder
from response import add_err_message_to_response, add_err_ko_message_to_response
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from data.encryption import aes_helper as aes
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel
from utils.time_price_info import get_time_price, get_additional_task_time_price

try:
    from utils.secrets import API_11ST_KEY
except ImportError:
    API_11ST_KEY = ''


# 11번가 예약 확인 데몬
# 1분 마다 체크 하도록 함
# 체크하여 주문이 있으면 생성하고 종료
# 만약 이미 db에 넣었다면 처리 하지 않음

base_url = 'https://homemaster-service.com'
ALREADY_PROCESSED = 'ALREADY_PROCESSED'
FAILED = 'FAILED'
SUCCEEDED = 'SUCCEEDED'

class BookingChecker:

    def __init__(self):
        self.logger = get_mongo_logger()

    def check_11st_new_orders_by_period(self, start_date, end_date):
        try:
            print start_date, end_date, dt.datetime.now()
            headers = {'openapikey' : API_11ST_KEY}
            r = requests.get('https://api.11st.co.kr/rest/ordservices/complete/%s/%s' % (start_date, end_date), headers = headers)
            ret = dict(xmltodict.parse(r.text))
            ret = ret['ns2:orders']

            del ret['@xmlns:ns2']
        except Exception, e:
            print_err_detail(e)
            self.logger.error('error new orders by period', extra = {'err' : str(e)})
            return []

        if 'ns2:result_code' in ret:
            self.logger.error('error new orders by period', extra = {'err' : ret['ns2:result_code']})
            return []

        order_ids = []

        for order in ret:
            if isinstance(ret[order], list):
                for order_detail in ret[order]:
                    order_ids.append(order_detail['ordNo'])
            else:
                order_ids.append(ret[order]['ordNo'])

        self.logger.debug('new orders by period', extra = {'start_date' : start_date, 'end_date' : end_date})
        return order_ids


    def check_11st_new_orders(self, start_date):
        all_order_ids = []

        for i in xrange(1):
            end_date = start_date + dt.timedelta(days = 7)

            start_date_param = dt.datetime.strftime(start_date, '%Y%m%d0000')
            end_date_param = dt.datetime.strftime(end_date, '%Y%m%d0000')
            order_ids = self.check_11st_new_orders_by_period(start_date_param, end_date_param)
            all_order_ids.extend(order_ids)

            start_date = end_date + dt.timedelta(days = 1)

        return all_order_ids


    def get_order_info(self, order_id):
        try:
            print 'request 11st ---------------------------------------------- start'
            url = 'http://api.11st.co.kr/rest/lifecategoryservices/reserveInfo/%s'
            url = url % order_id

            headers = {'openapikey' : API_11ST_KEY}
            r = requests.get(url, headers = headers)

            ret = xmltodict.parse(r.text)
            ret = ret['Reserve']
        except Exception, e:
            print 'request 11st ---------------------------------------------- exception'
            print_err_detail(e)
            self.logger.error('error get order info', extra = {'err' : str(e)})
            return {}

        order_dict = {}
        if ret['resultCode'] == '200':
            print 'request 11st ---------------------------------------------- response success'
            booking_info = ret['RsvInfo']
            for key in booking_info:
                order_dict[key] = booking_info[key]
        else:
            print 'request 11st ---------------------------------------------- response error'
            print 'error url : ', url
            print ret['resultCode'], ret['resultMessage']
            self.logger.error('error new orders by period', extra = {'err' : ret['resultMessage']})
            return {}

        self.logger.debug('get order info', extra = {'order_id' : order_id})
        print 'request 11st ------------------------------------------------ end'
        return order_dict


    def create_salt(selft):
        return base64.urlsafe_b64encode(uuid.uuid4().bytes)


    def create_password(self, salt):
        t_sha = hashlib.sha256()
        t_sha.update(salt + '123456')
        hashed_password =  base64.urlsafe_b64encode(t_sha.digest())

        return hashed_password


    def is_order_already_processed(self, order_id):
        session = Session()
        id_count = session.query(Order11st).filter(Order11st.order_id == order_id).count()

        return id_count > 0


    def register(self, name, phone):
        url = base_url + '/register'

        authsource  = '11st'
        email       = name + phone + '@11st.co.kr'
        salt        = self.create_salt()
        password    = self.create_password(salt) #123456

        params = {'name' : name, 'email' : email, 'salt' : salt, 'password' : password, 'phone' : phone, 'authsource' : authsource }

        try:
            response = requests.post(url, data = params)
            print response.text
            result = json.loads(response.text)
        except Exception, e:
            print_err_detail(e)
            self.logger.error('error register', extra = {'err' : str(e)})
            return '', False

        if 'err_code' in result or result['response'] == '':
            self.logger.error('error register', extra = {'err' : result['err_code']})
            return '', False

        user_id = result['response']
        self.logger.debug('11st register', extra = {'user_id' : user_id})

        return user_id, True


    def login(self, name, phone):
        session = Session()
        userdao = UserDAO()
        result = session.query(User) \
                    .filter(User.email == name + phone + '@11st.co.kr') \
                    .filter(User.authsource == '11st') \
                    .all()

        for row in result:
            key = userdao.get_user_salt_by_id(row.id)[:16]
            crypto = aes.MyCrypto(key)

            decrypted_name  = crypto.decodeAES(row.name)
            decrypted_phone = crypto.decodeAES(row.phone)

            if name == decrypted_name and phone == decrypted_phone: # 동명이인 고려, 일치하게 된다면 id 반환
                return row.id, True

        return '', False


    def add_address(self, user_id, address, kind, size):
        url = base_url + '/add_address'

        params = {'id' : user_id, 'address' : address, 'size' : size, 'kind' : kind}

        try:
            response = requests.post(url, data = params)
            result = json.loads(response.text)
        except Exception, e:
            print_err_detail(e)
            self.logger.error('error add address', extra = {'err' : str(e)})
            return '', False

        if 'err_code' in result or result['response'] == '':
            self.logger.error('error add address', extra = {'err' : result['err_code']})
            return '', False

        user_id = result['response']
        self.logger.debug('11st add address', extra = {'user_id' : user_id, 'address' : address, 'size' : size, 'kind' : kind})

        return user_id, True


    def add_booking(self, order_dict, user_id):
        print "add booking start ------------------------"
        try:
            session = Session()
            holder  = IntermediateValueHolder()

            if not 'lnkKey' in order_dict:
                print 'NO BOOKING ID - lnkKey'
                print '*' * 100
                return

            store_key = order_dict['lnkKey']

            print "store_key : " + store_key

            obj = holder.retrieve(store_key)
            if obj == None:
                print "holer.retrieve obj None ----------------------------"
                return [], False

            print "holer.retrieve obj not None ----------------------------"

            master_id           = obj['master_id']
            dates               = obj['dates']
            time                = obj['time']
            cleaning_duration   = obj['cleaning_duration']

            additional_time = 0
            if 'additional_time' in obj:
                additional_time     = obj['additional_time']

            order_id    = order_dict['ordNo']
            product_no  = order_dict['sellerPrdNo']

            if '_' in product_no:
                product_no  = product_no.split('_')
                appointment_type = int(product_no[2])
            else:
                appointment_type = 0

            # field
            request_id          = str(uuid.uuid4())
            #appointment_type    = int(product_no[2])
            message             = order_dict['rsvEtcInfo5'] if 'rsvEtcInfo5' in order_dict else ''
            trash_location      = '%s %s' % (order_dict['rsvEtcInfo1'], order_dict['rsvEtcInfo2'])
            havepet             = 0 if order_dict['rsvEtcInfo3'] == '아니오' else 1
            card_idx            = -1
            addr_idx            = 0

            options             = order_dict['RsvDtlsInfo']
            print options
            options_price       = sum([int(opt['optAmt']) for opt in options[1:]])
            options_name        = [opt['optNm'] for opt in options[1:]]

            additional_task     = 0

            if options_name != [None]:
                for opt in options_name:
                    if '창문' in opt:
                        additional_task += 1
                    elif '베란다' in opt:
                        additional_task += 2
                    elif '빨래' in opt:
                        additional_task += 4
                    elif '옷장' in opt:
                        additional_task += 8
                    elif '단문형' in opt:
                        additional_task += 16
                    elif '양문형' in opt:
                        additional_task += 32

            actual_price        = int(order_dict['rsvAmt'])
            price               = actual_price - options_price

            if appointment_type == 2 or appointment_type == 4:
                price /= (appointment_type * 2)
                actual_price = price + options_price

            now = dt.datetime.strftime(dt.datetime.now(), '%Y%m%d%H%M%S')
            hashids = Hashids(min_length = 16, salt = now + user_id)

            booking_ids = []
            index = 1

            for date in dates: #
                print date, time
                if index == 1:
                    booking_id = store_key
                else:
                    booking_id = hashids.encode(int(date + time.replace(':', '')))

                print 'key', booking_id

                date               = dt.datetime.strptime(date, '%Y%m%d')
                dow                = date.date().weekday()
                booking_time       = dt.time(hour = int(time.split(':')[0]), minute = int(time.split(':')[1]))

                start_time         = dt.datetime.combine(date, booking_time)
                estimated_end_time = start_time + dt.timedelta(minutes = cleaning_duration + additional_time)

                if index != 1:
                    actual_price = price
                    additional_task = 0
                    estimated_end_time -= dt.timedelta(minutes = additional_time)

                print "create booking -------------------------------------"

                booking = Booking(id = booking_id,
                                  request_id = request_id,
                                  user_id = user_id,
                                  master_id = master_id,
                                  appointment_type = appointment_type,
                                  appointment_index = index,
                                  dow = dow,
                                  booking_time = dt.datetime.now(),
                                  org_start_time = start_time,
                                  start_time = start_time,
                                  estimated_end_time = estimated_end_time,
                                  end_time = estimated_end_time, # update after homemaster finish their job
                                  cleaning_duration = cleaning_duration,
                                  additional_task = additional_task,
                                  price = price,
                                  price_with_task = actual_price,
                                  charging_price = 0,
                                  card_idx = card_idx,
                                  addr_idx = addr_idx,
                                  message = message,
                                  trash_location = trash_location,
                                  havepet = havepet,
                                  laundry_apply_all = 0,
                                  is_dirty = 0,
                                  master_gender = 0,
                                  source = '11st',
                                  status = BC.BOOKING_UPCOMMING,
                                  cleaning_status = BC.BOOKING_UPCOMMING,
                                  payment_status = BC.BOOKING_PAID)

                session.add(booking)
                index += 1

                booking_ids.append(booking_id)


            # remove store_key and related_keys
            store_key = obj['store_key']
            search_keys = obj['search_keys'].split(',')

            holder.remove(store_key)
            for sk in search_keys:
                holder.remove(sk)

            # order_11st에 order_id 추가 필요.
            print order_id
            order = Order11st(order_id = order_id)
            session.add(order)
            session.commit()

        except Exception, e:
            print_err_detail(e)
            self.logger.error('error in add booking', extra = {'err' : e})
        finally:
            session.close()

        print "add booking end ------------------------"

        return booking_ids, True


    def make_booking(self, order_dict):
        # check if already added
        order_id = order_dict['ordNo']
        if self.is_order_already_processed(order_id):
            print order_id, 'ALREADY_PROCESSED'
            return ALREADY_PROCESSED

        # register
        name = order_dict['rsvNm']
        phone = order_dict['telNo'].replace('-', '')
        user_id, reg_ok = self.register(name, phone)

        if reg_ok == False:
            user_id, login_ok  = self.login(name, phone)
            if login_ok == False:
                self.logger.error('11st failed to login', extra = {'name_' : name, 'phone' : phone})
                return FAILED

        print 'USER----------'
        self.logger.debug('11st success user access', extra = {'name_' : name, 'phone' : phone})
        print name, phone

        # add address
        address     = '%s %s' % (order_dict['addr'], order_dict['addrDtl'])
        product_no  = order_dict['sellerPrdNo']

        if '_' in product_no:
            product_no = product_no.split('_')
            kind = product_no[0]
            if kind == 'HOUSE':
                kind = 1
            elif kind == 'APT':
                kind = 2
            else:
                kind = 0 # officetel

            size = product_no[1]
        else:
            if product_no == 'OFFICE':
                kind = 0
                size = 12
            elif product_no == 'HOUSE1':
                kind = 1
                size = 13
            elif product_no == 'HOUSE2':
                kind = 2
                size = 24

        self.add_address(user_id, address, kind, size)

        print 'ADDRESS----------'
        print address, kind, size
        self.logger.debug('11st success add address', extra = {'address' : address, 'kind' : kind, 'size' : size})

        # add booking
        self.add_booking(order_dict, user_id)

        print 'BOOKING----------'
        for key in order_dict:
            print key, order_dict[key]
        print '*' * 200

        self.logger.debug('11st success add booking', extra = order_dict)

        return SUCCEEDED


if __name__ == '__main__':
    booking_checker = BookingChecker()
    now = dt.datetime.now()
    #now += dt.timedelta(days=-1)

    order_ids = booking_checker.check_11st_new_orders(now.date())

    for order_id in order_ids:
        print "order_id : ", order_id

    #order_info = booking_checker.get_order_info('201608029546710')
    #booking_checker.make_booking(order_info)

    for oid in order_ids:
        order_info = booking_checker.get_order_info(oid)
        '''for key in order_info:
            print key, order_info[key]'''
        booking_checker.make_booking(order_info)
