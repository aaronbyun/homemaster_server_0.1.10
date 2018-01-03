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
import booking_constant as BC
from sqlalchemy import and_, or_, func
from sender.sms_sender import SMS_Sender
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, Master, User, UserAddress, UserDefaultAddress, CancelReason
from data.dao.userdao import UserDAO
from data.dao.masterdao import MasterDAO
from data.encryption import aes_helper as aes
from utils.datetime_utils import convert_datetime_format
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from err.error_handler import print_err_detail, err_dict
from payment.payment_helper import request_payment, cancel_payment, request_charge
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel
from sender.alimtalk_sender import send_alimtalk
from sender.push_sender import send_all_bookings_canceled
try:
    from utils.stipulation_text import BOOKING_TYPE_DICT, BOOKING_CANCEL_ALL_TEXT, BOOKING_TEXT_SUBJECT
except ImportError:
    BOOKING_TYPE_DICT = {}
    BOOKING_CANCEL_ALL_TEXT = ''
    BOOKING_TEXT_SUBJECT = ''

try:
    from utils.secrets import MAIN_CALL, MANAGERS_CALL
except ImportError:
    MAIN_CALL = ''
    MANAGERS_CALL = ''

from utils.datetime_utils import convert_datetime_format


# 두달이 넘었는지 확인 한다.
# 전체 취소 시점 아직 두달이 안넘었다면 원래 내야할 과금만큼 더 매긴다.
# 넘었다면 깔끔하게 취소한다.

class CancelAllBookingForManagerHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        booking_id = self.get_argument('booking_id', '')
        reason_id = self.get_argument('reason_id', 0)
        etc_reason = self.get_argument('etc_reason', '')
        charge_amount = self.get_argument('charge_amount', 0)

        charge_amount = int(charge_amount)
        reason_id = int(reason_id)

        print 'cancel all charge amount : ', charge_amount

        ret = {}

        mongo_logger = get_mongo_logger()
        mix = get_mixpanel()

        try:
            session = Session()
            userdao = UserDAO()
            masterdao = MasterDAO()

            stmt = session.query(Booking.request_id).filter(Booking.id == booking_id).subquery()
            first_startime = session.query(Booking.start_time).filter(Booking.request_id == stmt).order_by(Booking.start_time).first()[0]

            result = session.query(Booking, Master, User, UserAddress) \
                         .join(Master, Booking.master_id == Master.id) \
                         .join(User, Booking.user_id == User.id) \
                         .join(UserDefaultAddress, User.id == UserDefaultAddress.user_id) \
                         .join(UserAddress, and_(UserAddress.user_id == UserDefaultAddress.user_id, UserAddress.user_addr_index == UserDefaultAddress.address_idx)) \
                         .filter(Booking.request_id == stmt) \
                         .filter(or_(Booking.cleaning_status == BC.BOOKING_UPCOMMING, Booking.cleaning_status == BC.BOOKING_STARTED)) \
                         .all()

            # 서비스를 처음 이용한지 2달이 넘었는지 아닌지 조사,
            # 넘지 않았다면 이미 부과된 금액에 대해서도 1회 서비스 금액 과의 차액만큼 부과됨
            current_time = dt.datetime.now()

            completed_charge = 1
            if current_time >= first_startime + dt.timedelta(days=57):
                completed_charge = 0


            cancel_all_charge = 0
            # 그동안의 모든 예약에 대해서 처리함
            for row in result:
                charge = 0

                new_status = BC.BOOKING_CANCELED_CHARGE

                bid = row.Booking.id
                user_id = row.Booking.user_id
                appointment_time = row.Booking.start_time
                current_status = row.Booking.status
                current_cleaning_status = row.Booking.cleaning_status
                current_payment_status = row.Booking.payment_status
                price = row.Booking.price_with_task

                diff_in_hours = (appointment_time - current_time).total_seconds() / 3600

                if diff_in_hours >= 24:
                    charge = price * BC.BOOKING_CHARGE_RATE_NO
                elif 4 <= diff_in_hours < 24:
                    charge = price * BC.BOOKING_CHARGE_RATE_30
                else:
                    charge = price * BC.BOOKING_CHARGE_RATE_50


                # 이미 지불한 금액에 대해 1회 비용의 차액만큼 계산
                if completed_charge == 1:
                    if current_cleaning_status == BC.BOOKING_COMPLETED:
                        # 차액만큼 계속 더함
                        cancel_all_charge += charge_amount


                if current_payment_status == BC.BOOKING_PAID and current_cleaning_status == BC.BOOKING_UPCOMMING:
                    new_status = BC.BOOKING_CANCELED_REFUND
                    '''
                    partial = '1'
                    if charge == 0:
                        partial = '0'

                    cancel_amount = int(price - charge)
                    if cancel_amount > 0:
                        ret_code, msg = cancel_payment(user_id, bid, cancel_amount, partial)
                        if ret_code == False:
                            session.close()
                            self.set_status(Response.RESULT_OK)
                            add_err_ko_message_to_response(ret, msg)
                            self.write(json.dumps(ret))
                            return   '''


                #row.Booking.modified_date   = current_time
                row.Booking.charging_price  = int(charge)
                row.Booking.status          = new_status
                row.Booking.cleaning_status = BC.BOOKING_CANCELED
                row.Booking.payment_status  = new_status

                # add cancel reason
                CANCEL_ALL = 1
                reason = session.query(CancelReason).filter(CancelReason.booking_id == bid)
                if reason.count() == 0:
                    cancel_reason = CancelReason(booking_id = bid, user_id = user_id, reason_id = reason_id,
                                                etc_reason = etc_reason, kind = CANCEL_ALL, cancel_time = dt.datetime.now())
                    session.add(cancel_reason)
                else:
                    reason_row = reason.one()
                    reason_row.kind = 1

            '''if cancel_all_charge > 0:
                user_name = userdao.get_user_name(user_id)
                ret_code, msg = request_charge(user_id, user_name, cancel_all_charge)
                if ret_code == False:
                    session.close()
                    self.set_status(Response.RESULT_OK)
                    add_err_ko_message_to_response(ret, msg)
                    self.write(json.dumps(ret))
                    return  '''

            key = userdao.get_user_salt_by_id(row.User.id)[:16]
            crypto = aes.MyCrypto(key)

            # push to homemaster via sms
            master_id = row.Master.id
            master_phone    = str(row.Master.phone)
            master_name     = str(row.Master.name)
            username        = str(crypto.decodeAES(row.User.name))
            userphone        = str(crypto.decodeAES(row.User.phone))
            date    = str(convert_datetime_format(row.Booking.start_time))
            addr    = str(crypto.decodeAES(row.UserAddress.address))
            appointment_type = str(row.Booking.appointment_type)

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
            #text = BOOKING_CANCEL_ALL_TEXT % (appointment_type, username, userphone, master_name, date)
            #send_result = sms_sender.send_for_manager(sender = MAIN_CALL, mtype = 'sms', to = MANAGERS_CALL, subject = BOOKING_TEXT_SUBJECT, text = text)

            for manager_phone in MANAGERS_CALL.split(','):
                send_alimtalk(manager_phone, 'noti_manager_cancel_all', username, date, appointment_type_text)

            master_pushkey = masterdao.get_master_pushkey(master_id)
            #send_all_bookings_canceled('android', [master_pushkey], booking_id, date)

            #send_alimtalk(master_phone, 'noti_manager_cancel_all', username, date, appointment_type_text)

            session.commit()

            mix.track(user_id, 'cancel all', {'time' : dt.datetime.now(), 'reason_id' : reason_id, 'etc_reason' : etc_reason})
            mongo_logger.debug('%s was all canceled' % booking_id, extra = {'user_id' : user_id, 'booking_id': booking_id})

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()
            self.write(json.dumps(ret))
