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
import requests
import datetime as dt
import booking_constant as BC
from hashids import Hashids
from data.session.mysql_session import engine, Session
from data.model.data_model import UserPaymentRecord, Booking, UserDefaultAddress, UserDefaultCard
from data.dao.userdao import UserDAO 
from data.dao.addressdao import AddressDAO
from data.dao.masterdao import MasterDAO
from data.dao.promotiondao import PromotionDAO
from data.intermediate.value_holder import IntermediateValueHolder
from utils.datetime_utils import time_to_str, time_to_minutes, timedelta_to_time
from err.error_handler import print_err_detail, err_dict
from response import Response
from response import add_err_message_to_response
from sqlalchemy.exc import IntegrityError
from sender.sms_sender import send_booking_iphone
from payment.payment_helper import request_payment
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from data.mixpanel.mixpanel_helper import get_mixpanel
from logger.mongo_logger import get_mongo_logger

class RequestBookingForManagerHandler(tornado.web.RequestHandler):
    def post(self):
            self.set_header("Content-Type", "application/json")

            ret = {}

            store_key               = self.get_argument('store_key', '')
            uid                     = self.get_argument('uid', '')
            mid                     = self.get_argument('mid', '')
            appointment_type        = self.get_argument('appointment_type', BC.ONE_TIME)
            additional_task         = self.get_argument('additional_task', 0)
            discounted_price        = self.get_argument('discounted_price', 0)
            price                   = self.get_argument('price', 0)
            price_with_task         = self.get_argument('price_with_task', 0)
            promotion_code          = self.get_argument('promotion_code', '')
            have_pet                = self.get_argument('have_pet', 0)
            search_keys             = self.get_argument('search_keys', '')
            master_gender           = self.get_argument('master_gender', 0)
            isdirty                 = self.get_argument('isdirty', 0)
            first_added_time        = self.get_argument('first_added_time', 0)
            additional_time         = self.get_argument('additional_time', 10)
            laundry_apply_all       = self.get_argument('laundry_apply_all', 0) # 0 - one time, 1 - all time

            # convert datetime
            appointment_type        = int(appointment_type)
            additional_task         = int(additional_task)
            price                   = int(price)
            price_with_task         = int(price_with_task)
            discounted_price        = int(discounted_price)
            have_pet                = int(have_pet)
            master_gender           = int(master_gender)
            isdirty                 = int(isdirty)
            laundry_apply_all       = int(laundry_apply_all)

            first_added_time        = int(first_added_time)
            additional_time         = int(additional_time)
            first_added_time_in_minutes   = first_added_time * 6
            additional_time_in_minutes    = additional_time * 6 

            search_keys = search_keys.split(',')

            havetools = 1
            if additional_task >= 64:
                havetools = 0

            mongo_logger = get_mongo_logger()

            mongo_logger.debug('%s request booking' % uid, extra = {    'uid' : uid, 'mid' : mid,
                                                                        'appointment_type' : appointment_type, 
                                                                        'have_pet' : have_pet, 'master_gender' : master_gender,
                                                                        'isdirty' : isdirty})

            mix = get_mixpanel()

            try:
                session = Session()
                userdao = UserDAO()
                promotiondao = PromotionDAO()

                holder = IntermediateValueHolder()

                card_idx = 0
                addr_idx = 0

                # get card and address idx
                addr_idx = userdao.get_user_default_address_index(uid)
                card_idx = userdao.get_user_default_card_index(uid)

                # hasids to generate unique booking id
                now = dt.datetime.strftime(dt.datetime.now(), '%Y%m%d%H%M%S')
                hashids = Hashids(min_length = 16, salt = now + uid)
                print 'salt : ', now + uid

                # request id to group each individual bookings
                request_id = str(uuid.uuid4())

                obj = holder.retrieve(store_key)
                if obj == None:
                    session.close()
                    self.set_status(Response.RESULT_OK)
                    add_err_message_to_response(ret, err_dict['err_booking_timeout'])
                    self.write(json.dumps(ret)) 
                    return  

                i = 1
                booking_ids = []
                start_time_list = []

                obj = sorted(obj, key = lambda x: x['date'])

                for item in obj:
                    
                    booking_id = hashids.encode(int(item['date'] + time_to_str(item['start_time'])))
                    master_id = item['mid']

                    print item['date'], booking_id

                    dow                = dt.datetime.strptime(item['date'], '%Y%m%d').date().weekday()
                    start_time         = dt.datetime.combine(dt.datetime.strptime(item['date'], '%Y%m%d'), item['start_time'])
                    estimated_end_time = dt.datetime.combine(dt.datetime.strptime(item['date'], '%Y%m%d'), item['end_time'])

                    cleaning_duration = time_to_minutes(timedelta_to_time(estimated_end_time - dt.timedelta(minutes=additional_time_in_minutes + first_added_time_in_minutes) - start_time))

                    actual_price = 0
                    if i == 1: # 1 번째 클리닝
                        actual_price = price_with_task - discounted_price # 할인은 1회만 적용됨

                    else: # 나머지
                        actual_price = price
                        if havetools == 1:
                            additional_task = 0
                        else: 
                            additional_task = 64
                            actual_price += BC.VACCUM_CHARGE

                        if laundry_apply_all == 1:
                            additional_task += 4 # 빨래

                        isdirty = 0 # 첫째 이후에는 is dirty는 0
                        estimated_end_time = estimated_end_time - dt.timedelta(minutes=additional_time_in_minutes + first_added_time_in_minutes)


                    booking = Booking(id = booking_id, 
                                      request_id = request_id, 
                                      user_id = uid, 
                                      master_id = mid, 
                                      appointment_type = appointment_type, 
                                      appointment_index = i,
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
                                      havetools = havetools, 
                                      havepet = have_pet,
                                      is_dirty = isdirty,
                                      master_gender = master_gender,
                                      status = BC.BOOKING_UPCOMMING)
                    i += 1

                    session.add(booking) 
                    booking_ids.append(booking_id)
                    start_time_list.append(start_time)

                    #print 'booking_id', booking_id, 'was added..'

                if True:
                    session.commit()

                    # remove store_key and related_keys
                    holder.remove(store_key)
                    for sk in search_keys:
                        holder.remove(sk)

                    # promotion code 와 연결
                    if promotion_code != '':
                        promotiondao.set_promotion_code_status(promotion_code, 1, booking_ids[0], price_with_task)


                    send_booking_iphone(booking_ids[0])

                    mix.track(uid, 'request booking', {'time' : dt.datetime.now(), 'appointment_type' : appointment_type, 'additional_task' : additional_task})
                    mongo_logger.debug('%s made reservation' % uid, extra = {'user_id' : uid, 'master_id' : mid, 'booking_id' : booking_ids[0], 'start_time' : start_time_list[0]})
                    ret['response'] = {'booking_ids' : booking_ids}
                    self.set_status(Response.RESULT_OK)
                else: # 결제 에러인 경우
                    session.close()
                    self.set_status(Response.RESULT_OK)
                    add_err_message_to_response(ret, err_dict['err_booking_payment'])
                    self.write(json.dumps(ret)) 
                    return 
                
            except Exception, e:
                session.rollback()
                add_err_message_to_response(ret, err_dict['err_mysql'])
                self.set_status(Response.RESULT_SERVERERROR)
                print_err_detail(e)

            finally:
                session.close()
                self.write(json.dumps(ret))
