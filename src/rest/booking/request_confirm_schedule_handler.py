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
from data.model.data_model import UserPaymentRecord, Booking, UserDefaultAddress, UserDefaultCard, User, MasterPushKey, UserFreeEvent
from data.dao.userdao import UserDAO
from data.dao.addressdao import AddressDAO
from data.dao.masterdao import MasterDAO
from data.dao.promotiondao import PromotionDAO
from data.dao.coupondao import CouponDAO
from data.dao.addressdao import AddressDAO
from data.intermediate.value_holder import IntermediateValueHolder
from utils.datetime_utils import time_to_str, time_to_minutes, timedelta_to_time
from err.error_handler import print_err_detail, err_dict
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from sqlalchemy.exc import IntegrityError
from payment.payment_helper import request_payment
from sender.sms_sender import send_booking_iphone
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel
from sender.sms_sender import send_booking_requested
from sender.push_sender import send_new_booking_notification
from utils.datetime_utils import convert_datetime_format2
from sender.alimtalk_sender import send_alimtalk
from sender.sms_sender import additional_task_string
from sender.jandi_sender import send_jandi
from sender.message_sender import MessageSender
try:
    from utils.secrets import MANAGERS_CALL
except ImportError:
    MANAGERS_CALL = ''

class RequestConfirmScheduleHandler(tornado.web.RequestHandler):
    def post(self):
            self.set_header("Content-Type", "application/json")
            self.set_header('Access-Control-Allow-Origin', '*')

            ret = {}

            uid                     = self.get_argument('uid', '')
            search_keys             = self.get_argument('search_keys', '')
            store_key               = self.get_argument('store_key', '')

            price                   = self.get_argument('price', 0)
            price_with_task         = self.get_argument('price_with_task', 0)

            wage_per_hour           = self.get_argument('wage_per_hour', 0)
            address_index           = self.get_argument('address_index', 0)

            discounted_price        = self.get_argument('discounted_price', 0)
            promotion_code          = self.get_argument('promotion_code', '')

            coupon_id               = self.get_argument('coupon_id', '')
            coupon_discount_price   = self.get_argument('coupon_discount_price', 0)

            laundry_apply_all       = self.get_argument('laundry_apply_all', 0) # -1 - 없앰, 0 - one time, 1 - all time

            user_type               = self.get_argument('user_type', 'unknown')

            # convert datetime

            # for ios fix
            if discounted_price != 0:
                discounted_price = discounted_price.replace('Optional(', '').replace(')', '')

            price                   = int(price)
            price_with_task         = int(price_with_task)
            discounted_price        = int(discounted_price)
            coupon_discount_price   = int(coupon_discount_price)
            laundry_apply_all       = int(laundry_apply_all)
            wage_per_hour           = int(wage_per_hour)

            print 'price_with_task', price_with_task
            print 'discounted_price', discounted_price

            search_keys = search_keys.split(',')

            mongo_logger = get_mongo_logger()
            mix = get_mixpanel()

            try:
                session = Session()
                userdao = UserDAO()
                masterdao = MasterDAO()
                promotiondao = PromotionDAO()
                addressdao = AddressDAO()
                coupondao = CouponDAO()

                holder = IntermediateValueHolder()

                # request id to group each individual bookings
                request_id = str(uuid.uuid4())

                obj = holder.retrieve(store_key)
                print obj
                if obj == None:
                    self.set_status(Response.RESULT_OK)
                    add_err_message_to_response(ret, err_dict['err_booking_timeout'])
                    mix.track(uid, 'request timeout', {'time' : dt.datetime.now()})
                    mongo_logger.error('%s got timed out' % uid)
                    return

                # retrieve all stored values
                uid                 = obj['user_id']
                mid                 = obj['master_id']
                dates               = obj['dates']
                time                = obj['time']
                appointment_type    = obj['appointment_type']
                additional_task     = obj['additional_task']
                org_additional_task = additional_task

                taking_time         = obj['taking_time']
                first_added_time    = obj['first_added_time']
                additional_time     = obj['additional_time']
                total_time          = obj['total_time']
                master_gender       = obj['master_gender']
                have_pet            = obj['have_pet']
                isdirty             = obj['isdirty']

                is_b2b    = userdao.is_b2b(uid)

                # hasids to generate unique booking id
                now = dt.datetime.strftime(dt.datetime.now(), '%Y%m%d%H%M%S')
                hashids = Hashids(min_length = 16, salt = now + uid)

                # set tool info
                havetools = 1
                if additional_task >= 64:
                    havetools = 0

                card_idx = 0
                addr_idx = 0


                # get card and address idx
                if is_b2b:
                    addr_idx = address_index
                else:
                    addr_idx = userdao.get_user_default_address_index(uid)

                card_idx = userdao.get_user_default_card_index(uid)

                i = 1
                booking_ids = []
                start_time_list = []

                for date in dates: #
                    print date, time
                    booking_id = hashids.encode(int(date + time.replace(':', '')))
                    print 'key', booking_id
                    master_id  = mid

                    date               = dt.datetime.strptime(date, '%Y%m%d')
                    dow                = date.date().weekday()
                    booking_time       = dt.time(hour = int(time.split(':')[0]), minute = int(time.split(':')[1]))

                    start_time         = dt.datetime.combine(date, booking_time)
                    estimated_end_time = start_time + dt.timedelta(minutes = total_time)
                    cleaning_duration  = taking_time

                    actual_price = 0
                    if i == 1: # 1 번째 클리닝
                        actual_price = price_with_task - (discounted_price + coupon_discount_price) # 할인은 1회만 적용됨

                    else: # 나머지
                        actual_price = price
                        if havetools == 1:
                            additional_task = 0
                        else:
                            additional_task = 64

                        if laundry_apply_all == 1:
                            additional_task += 4 # 빨래

                        isdirty = 0 # 첫째 이후에는 is dirty는 0
                        estimated_end_time = estimated_end_time - dt.timedelta(minutes = additional_time + first_added_time)

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
                                      laundry_apply_all = laundry_apply_all,
                                      is_dirty = isdirty,
                                      master_gender = master_gender,
                                      user_type = user_type,
                                      wage_per_hour = wage_per_hour,
                                      status = BC.BOOKING_UPCOMMING,
                                      cleaning_status = BC.BOOKING_UPCOMMING,
                                      payment_status = BC.BOOKING_UNPAID_YET)
                    i += 1

                    session.add(booking)
                    booking_ids.append(booking_id)
                    start_time_list.append(start_time)

                    #print 'booking_id', booking_id, 'was added..'

                # charge for first appointment date
                user_name = userdao.get_user_name(uid)


                if is_b2b:
                    session.commit()

                    # remove store_key and related_keys
                    holder.remove(store_key)
                    for sk in search_keys:
                        holder.remove(sk)

                    send_jandi('NEW_BOOKING', '[b2b]새 예약 알림', 'b2b 고객님 예약완료', user_name)

                    # b2b용 알림톡 추가 필요

                    ret['response'] = booking_ids[0]
                    self.set_status(Response.RESULT_OK)

                    mongo_logger.debug('b2b confirm booking', extra = {'user_id' : uid, 'master_id' : mid, 'booking_id' : booking_ids[0]})

                    return

                charge_price = price_with_task - (discounted_price + coupon_discount_price)

                # 1주 1회면서, 이벤트 기간인 경우에는 결제 하지 않음
                import redis
                try:
                    from utils.secrets import REDIS_HOST, REDIS_PORT, REDIS_PWD
                except ImportError:
                    REDIS_HOST = 'localhost'
                    REDIS_PORT = 6379
                    REDIS_PWD = ''

                r = redis.Redis(host = REDIS_HOST, port = REDIS_PORT, password = REDIS_PWD)
                event_on = r.get('free_event')

                print event_on
                if appointment_type == 4 and event_on:
                    charge_price = price_with_task - price

                    # 1회 이벤트 고객임을 명시해야함
                    # table 필요
                    free_event = UserFreeEvent(booking_request_id=request_id, user_id=uid, datetime=dt.datetime.now())
                    session.add(free_event)

                if charge_price <= 0:
                    ret_code = True
                    msg = ''
                else:
                    ret_code, msg = request_payment(uid, user_name, booking_ids[0], charge_price, appointment_type)

                # 결제 정보 출력
                print user_name, ret_code, msg

                if ret_code:
                    session.commit()

                    # remove store_key and related_keys
                    holder.remove(store_key)
                    for sk in search_keys:
                        holder.remove(sk)

                    # promotion code 와 연결
                    if promotion_code != '':
                        promotiondao.set_promotion_code_status(promotion_code, 1, booking_ids[0], price_with_task)

                    if coupon_id != '':
                        coupondao.set_coupon_status(coupon_id, 1, booking_ids[0], price_with_task)

                    # change status to paid
                    try:
                        first_booking = session.query(Booking, User, MasterPushKey) \
                                                .join(User, Booking.user_id == User.id) \
                                                .outerjoin(MasterPushKey, Booking.master_id == MasterPushKey.master_id) \
                                                .filter(Booking.id == booking_ids[0]) \
                                                .one()
                    except NoResultFound, e:
                        session.close()
                        self.set_status(Response.RESULT_OK)
                        mongo_logger.debug('no first booking record', extra = {    'uid' : uid, 'mid' : mid,'appointment_type' : appointment_type, 'have_pet' : have_pet, 'master_gender' : master_gender, 'isdirty' : isdirty})
                        add_err_message_to_response(ret, err_dict['err_no_record'])
                        return

                    except MultipleResultsFound, e:
                        session.close()
                        self.set_status(Response.RESULT_OK)
                        mongo_logger.debug('multiple first booking record', extra = {    'uid' : uid, 'mid' : mid, 'appointment_type' : appointment_type, 'have_pet' : have_pet, 'master_gender' : master_gender, 'isdirty' : isdirty})
                        add_err_message_to_response(ret, err_dict['err_multiple_record'])
                        return

                    for bid in booking_ids:
                        print 'booking_id', bid, 'was added successfully...'

                    tid = msg
                    first_booking.Booking.tid               = tid
                    first_booking.Booking.status            = BC.BOOKING_PAID
                    first_booking.Booking.clearning_status  = BC.BOOKING_UPCOMMING
                    first_booking.Booking.payment_status    = BC.BOOKING_PAID

                    cleaning_time   = convert_datetime_format2(first_booking.Booking.start_time)
                    devicetype      = first_booking.User.devicetype
                    master_pushkey  = first_booking.MasterPushKey.pushkey if first_booking.MasterPushKey != None else ''

                    session.commit()

                    mix.track(uid, 'confirm booking', {'time' : dt.datetime.now(), 'appointment_type' : appointment_type, 'additional_task' : additional_task})
                    mongo_logger.debug('confirm booking', extra = {'log_time' : dt.datetime.now(), 'user_id' : uid, 'master_id' : mid, 'booking_id' : booking_ids[0], 'start_time' : start_time_list[0]})

                    #ret['response'] = {'booking_ids' : booking_ids} # victor 요청으로 첫번째
                    ret['response'] = booking_ids[0]
                    self.set_status(Response.RESULT_OK)

                    # notification to iphone users
                    #send_booking_iphone(booking_ids[0]) # ios released!! 03.23

                    # alimtalk
                    phone = userdao.get_user_phone(uid)
                    appointment_type_text = ''
                    if appointment_type == BC.ONE_TIME or appointment_type == BC.ONE_TIME_BUT_CONSIDERING:
                        appointment_type_text = '1회'
                    elif appointment_type == BC.FOUR_TIME_A_MONTH:
                        appointment_type_text = '매주'
                    elif appointment_type == BC.TWO_TIME_A_MONTH:
                        appointment_type_text = '2주 1회'
                    elif appointment_type == BC.ONE_TIME_A_MONTH:
                        appointment_type_text = '4주 1회'

                    service = '기본 클리닝'
                    if org_additional_task != 0:
                        service += ', {}'.format(additional_task_string(org_additional_task))

                    if len(phone) > 11:
                        phone = phone[:11]

                    # jandi notification
                    user_address, _, _ = userdao.get_user_address_by_index(uid, addr_idx)
                    district = addressdao.get_gu_name(userdao.get_user_address(uid)[0])
                    print district

                    master_name = masterdao.get_master_name(mid)
                    master_phone = masterdao.get_master_phone(mid)

                    send_jandi('NEW_BOOKING', '[{}] 새 예약 알림'.format(user_type), user_name + ' 고객님 예약됨', '({}), {} 홈마스터, {}, {}'.format(district, master_name, start_time_list[0], appointment_type_text))

                    send_alimtalk(phone, 'noti_reservation', user_name, cleaning_time, appointment_type_text, service, 'http://goo.gl/j6PByf')
                    send_alimtalk(phone, 'noti_caution',     'https://goo.gl/FxrJML', 'http://goo.gl/kuCVIh')

                    # notification to homemaster
                    send_new_booking_notification('android', [master_pushkey], booking_ids[0], cleaning_time)

                    content = '''안녕하세요 {} 홈마스터님, 새로운 예약 정보를 알려드립니다.

                    날짜 : {}
                    주소 : {}
                    주기/서비스 : {} {}

                    자세한 내용은 마스터님 앱에서 확인 부탁 드립니다 ^^'''.format(master_name, convert_datetime_format2(start_time_list[0]),
                                                             user_address,
                                                             appointment_type_text,
                                                             service
                                                             )
                    message_sender = MessageSender()
                    print master_phone
                    message_sender.send([master_phone], '새로운 예약 알림', content)

                else: # 결제 에러인 경우
                    session.close()
                    self.set_status(Response.RESULT_OK)
                    add_err_ko_message_to_response(ret, msg)
                    ret['err_code'] = '5000' # 임시 처리
                    mongo_logger.debug('request booking failed to charge', extra = {    'user_id' : uid, 'master_id' : mid,
                                                                        'appointment_type' : appointment_type,
                                                                        'have_pet' : have_pet, 'master_gender' : master_gender,
                                                                        'isdirty' : isdirty})
                    return

            except Exception, e:
                session.rollback()
                add_err_message_to_response(ret, err_dict['err_mysql'])
                mongo_logger.debug('request booking failed', extra = {    'user_id' : uid, 'master_id' : mid,
                                                                        'appointment_type' : appointment_type,
                                                                        'have_pet' : have_pet, 'master_gender' : master_gender,
                                                                        'isdirty' : isdirty})
                self.set_status(Response.RESULT_SERVERERROR)
                print_err_detail(e)

            finally:
                session.close()
                self.write(json.dumps(ret))
