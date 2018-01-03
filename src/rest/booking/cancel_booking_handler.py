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
from sqlalchemy import and_, or_
from sender.sms_sender import SMS_Sender
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, Master, User, UserAddress, UserDefaultAddress, CancelReason, UserFreeEvent
from data.dao.userdao import UserDAO
from data.dao.masterdao import MasterDAO
from data.dao.coupondao import CouponDAO
from data.encryption import aes_helper as aes
from utils.datetime_utils import convert_datetime_format
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from payment.payment_helper import request_payment, cancel_payment
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel
from sender.alimtalk_sender import send_alimtalk
from sender.push_sender import send_booking_canceled
from sender.jandi_sender import send_jandi
from sender.message_sender import MessageSender

try:
    from utils.stipulation_text import BOOKING_TYPE_DICT, BOOKING_CANCEL_TEXT, BOOKING_TEXT_SUBJECT
except ImportError:
    BOOKING_TYPE_DICT = {}
    BOOKING_CANCEL_TEXT = ''
    BOOKING_TEXT_SUBJECT = ''

try:
    from utils.secrets import MAIN_CALL, MANAGERS_CALL
except ImportError:
    MAIN_CALL = ''
    MANAGERS_CALL = ''

from utils.datetime_utils import convert_datetime_format

CANCEL_ADMIN = 8

class CancelBookingHandler(tornado.web.RequestHandler):

    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        booking_id = self.get_argument('booking_id', '')
        reason_id = self.get_argument('reason_id', CANCEL_ADMIN)
        etc_reason = self.get_argument('etc_reason', '')
        no_fee = self.get_argument('no_fee', 0)

        reason_id = int(reason_id)

        print "reason_id : ", reason_id

        no_fee = int(no_fee)

        ret = {}

        mongo_logger = get_mongo_logger()
        mix = get_mixpanel()

        try:
            session = Session()

            try:
                row = session.query(Booking, Master, User, UserAddress) \
                             .join(Master, Booking.master_id == Master.id) \
                             .join(User, Booking.user_id == User.id) \
                             .join(UserDefaultAddress, User.id == UserDefaultAddress.user_id) \
                             .join(UserAddress, and_(UserAddress.user_id == UserDefaultAddress.user_id, UserAddress.user_addr_index == UserDefaultAddress.address_idx)) \
                             .filter(Booking.id == booking_id) \
                             .filter(Booking.cleaning_status == BC.BOOKING_UPCOMMING) \
                             .one()

            except NoResultFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_no_entry_to_cancel'])
                return

            user_id         = row.Booking.user_id

            masterdao = MasterDAO()
            userdao = UserDAO()
            key = userdao.get_user_salt_by_id(user_id)[:16]
            crypto = aes.MyCrypto(key)

            # push to homemaster via sms
            master_id = row.Master.id

            master_phone    = str(row.Master.phone)
            master_name     = str(row.Master.name)
            username        = str(crypto.decodeAES(row.User.name))
            userphone        = str(crypto.decodeAES(row.User.phone))
            date    = str(convert_datetime_format(row.Booking.start_time))
            addr    = str(crypto.decodeAES(row.UserAddress.address))


            charge = 0
            new_status = BC.BOOKING_CANCELED_CHARGE

            request_id      = row.Booking.request_id

            appointment_index = row.Booking.appointment_index
            appointment_time = row.Booking.start_time
            appointment_type = row.Booking.appointment_type
            current_status = row.Booking.status
            current_cleaning_status = row.Booking.cleaning_status
            current_payment_status = row.Booking.payment_status
            price = row.Booking.price_with_task
            source = row.Booking.source
            device_type = row.Booking.user_type
            now = dt.datetime.now()
            cancel_amount = 0

            diff_in_hours = (appointment_time - now).total_seconds() / 3600

            if diff_in_hours >= 24:
                charge = price * BC.BOOKING_CHARGE_RATE_NO
            elif 4 <= diff_in_hours < 24:
                charge = price * BC.BOOKING_CHARGE_RATE_30
            else:
                charge = price * BC.BOOKING_CHARGE_RATE_50

            if current_payment_status == BC.BOOKING_PAID:
                if no_fee == 1: # 관리자가 선택하여 fee를 지불 할 수 있게 하기 위해서
                    charge = 0

                new_status = BC.BOOKING_CANCELED_REFUND

                partial = '1'
                if charge == 0:
                    partial = '0'

                is_event = session.query(UserFreeEvent) \
                                .filter(UserFreeEvent.booking_request_id == request_id) \
                                .first()

                is_event = True if is_event != None else False

                cancel_amount = int(price - charge)
                if cancel_amount > 0 and source == 'hm' and userdao.get_user_default_card_index(user_id) != -1:
                    if not (is_event and appointment_index == 1):
                        ret_code, msg = cancel_payment(user_id, booking_id, cancel_amount, partial)
                        if ret_code == False:
                            session.close()
                            self.set_status(Response.RESULT_OK)
                            add_err_ko_message_to_response(ret, msg)
                            #self.write(json.dumps(ret))
                            return
                    else:
                        # 결제 필요
                        # 취소에 대한 결제 필요
                        partial = '0'
                        cancel_amount = row.Booking.price_with_task - row.Booking.price
                        if cancel_amount > 0:
                            cancel_payment(user_id, booking_id, cancel_amount, partial)

                        complete_count = session.query(Booking) \
                                .filter(Booking.request_id == request_id) \
                                .filter(Booking.cleaning_status == 2) \
                                .count()

                        print complete_count, row.Booking.cleaning_status
                        if complete_count < 9 and row.Booking.cleaning_status == 2:
                            ret_code, msg = request_payment(user_id, username, booking_id, price, appointment_type)
                            if ret_code == False:
                                row.Booking.payment_status = BC.BOOKING_PAYMENT_FAILED


            else: # cancel charge price
                print 'cancel charge'
                charging_price = int(charge)
                if charging_price > 0 and source == 'hm' and userdao.get_user_default_card_index(user_id) != -1 and no_fee == 0:
                    print user_id, username, booking_id, charging_price, appointment_type

                    ret_code, msg = request_payment(user_id, username, booking_id, charging_price, appointment_type)
                    if ret_code == False:
                        new_status = BC.BOOKING_PAYMENT_FAILED

            #row.Booking.modified_date   = now
            row.Booking.charging_price  = int(charge)
            row.Booking.status          = new_status
            row.Booking.cleaning_status = BC.BOOKING_CANCELED
            row.Booking.payment_status  = new_status

            appointment_type_text = ''
            if appointment_type == BC.ONE_TIME or appointment_type == BC.ONE_TIME_BUT_CONSIDERING:
                appointment_type_text = '1회'
            elif appointment_type == BC.FOUR_TIME_A_MONTH:
                appointment_type_text = '매주'
            elif appointment_type == BC.TWO_TIME_A_MONTH:
                appointment_type_text = '2주 1회'
            elif appointment_type == BC.ONE_TIME_A_MONTH:
                appointment_type_text = '4주 1회'

            #sms_sender = SMS_Sender()
            #text = BOOKING_CANCEL_TEXT % (username, userphone, master_name, date)
            #print sms_sender.send_for_manager(sender = MAIN_CALL, mtype = 'sms', to = MANAGERS_CALL, subject = BOOKING_TEXT_SUBJECT, text = text)
            #for manager_phone in MANAGERS_CALL.split(','):
            #    send_alimtalk(manager_phone, 'noti_manager_cancel', username, date, appointment_type_text)

            cancel_reasons = []
            cancel_reasons.append('지금은 서비스가 필요하지 않아요')
            cancel_reasons.append('집에 없어서 문을 열어드릴 수가 없어요')
            cancel_reasons.append('시간이 마음에 들지 않아요')
            cancel_reasons.append('클리닝을 잊고 있었네요')
            cancel_reasons.append('원하는 홈마스터가 아니에요')
            cancel_reasons.append('기타')
            cancel_reasons.append('이사가요')
            cancel_reasons.append('기타')
            cancel_reasons.append('관리자가 취소 했습니다')

            cancel_reason = cancel_reasons[reason_id]
            if cancel_reason == '기타':
                cancel_reason += ' ' + etc_reason
            elif reason_id == CANCEL_ADMIN:
                cancel_reason += ', 관리자 메모 : ' + etc_reason

            send_jandi('NEW_BOOKING', "취소 알림", username + ' 고객님 취소함', '{}, {}, 사유 : {}'.format(date, appointment_type_text, cancel_reason))
            print 'jandi notification for cancel...'

            master_pushkey = masterdao.get_master_pushkey(master_id)
            #master_name = masterdao.get_master_name(master_id)
            #master_phone   = masterdao.get_master_phone(master_id)

            send_booking_canceled('android', [master_pushkey], booking_id, date, username)

            content = '''{} 홈마스터님
예약이 1회 취소 되었습니다.

고객 : {}
주기 : {}
날짜 : {}'''.format(master_name, username, appointment_type_text, date)

            message_sender = MessageSender()
            message_sender.send([master_phone], '예약 1회 취소 알림', content)

            print 'master_pushkey', master_pushkey
            print booking_id, date

            #send_alimtalk(master_phone, 'noti_manager_cancel', username, date, appointment_type_text)
            # adjust appointment index
            index_result = session.query(Booking).filter(Booking.request_id == request_id).filter(Booking.appointment_index > appointment_index).all()
            for index_row in index_result:
                index_row.appointment_index -= 1

            coupondao = CouponDAO()
            coupondao.cancel_coupon_usage(booking_id)

            CANCEL = 0
            cancel_reason = CancelReason(booking_id = booking_id, user_id = user_id, reason_id = reason_id,
                                         etc_reason = etc_reason, kind = CANCEL, cancel_time = dt.datetime.now())
            session.add(cancel_reason)

            session.commit()

            mix.track(user_id, 'cancel', {'time' : dt.datetime.now(), 'reason_id' : reason_id, 'etc_reason' : etc_reason, 'cancel_amount' : cancel_amount})
            mongo_logger.debug('%s was canceled' % booking_id, extra = {'user_id' : user_id, 'booking_id' : booking_id, 'cancel_amount' : cancel_amount})

            ret['response'] = Response.SUCCESS

            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
            mongo_logger.error('error occurred when calcelling booking', extra = {'err' : str(e)})

        finally:
            session.close()
            self.write(json.dumps(ret))
