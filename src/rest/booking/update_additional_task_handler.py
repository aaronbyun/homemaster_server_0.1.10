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
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, UserFreeEvent
from data.dao.masterdao import MasterDAO
from data.dao.userdao import UserDAO
from data.dao.addressdao import AddressDAO
from data.intermediate.value_holder import IntermediateValueHolder
from utils.datetime_utils import convert_datetime_format, time_to_minutes, timedelta_to_time
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from err.error_handler import print_err_detail, err_dict
from utils.stipulation_text import BOOKING_TYPE_DICT, BOOKING_UPDATE_TEXT, BOOKING_TEXT_SUBJECT
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import or_
from payment.payment_helper import cancel_payment, request_payment
from sender.sms_sender import send_updated_text
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel
from sender.alimtalk_sender import send_alimtalk
from sender.sms_sender import additional_task_string
try:
    from utils.secrets import MANAGERS_CALL
except ImportError:
    MANAGERS_CALL = ''


class UpdateAdditionalTaskHandler(tornado.web.RequestHandler):

    def post(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        booking_id              = self.get_argument('booking_id', '')
        additional_task         = self.get_argument('additional_task', '')
        new_price               = self.get_argument('new_price', 0)
        total_taking_time       = self.get_argument('total_taking_time', '')
        laundry_apply_all       = self.get_argument('laundry_apply_all', 0) # -2 - 전체없앰 -1 - 하나 없앰, 0 - one time, 1 - all time

        # convert parameter
        new_price                    = int(new_price)
        additional_task              = int(additional_task)
        total_taking_time            = int(total_taking_time)
        total_taking_time_in_minutes = total_taking_time * 6
        laundry_apply_all            = int(laundry_apply_all)

        print 'update additional task params'
        print booking_id
        print additional_task
        print new_price
        print total_taking_time
        print laundry_apply_all

        mix = get_mixpanel()
        mongo_logger = get_mongo_logger()

        try:
            print 'total_minutes :', total_taking_time_in_minutes
            if total_taking_time_in_minutes >= 720:
                self.set_status(Response.RESULT_OK)
                add_err_ko_message_to_response(ret, '클리닝 가능 시간을 초과하였습니다. (최대 12시간) 이전 화면으로 돌아가 추가사항을 2개이하로 줄여주세요.')
                return

            session = Session()
            masterdao = MasterDAO()
            userdao = UserDAO()

            holder = IntermediateValueHolder()

            row = session.query(Booking).filter(Booking.id == booking_id).one()

            uid                 = row.user_id
            start_time          = row.start_time
            end_time            = row.estimated_end_time
            request_id          = row.request_id
            appointment_index   = row.appointment_index
            appointment_type    = row.appointment_type
            payment_status      = row.payment_status
            price_with_task     = row.price_with_task

            isdirty             = row.is_dirty
            if isdirty == 1:
                total_taking_time_in_minutes += 120

            org_taking_time_in_minutes = time_to_minutes(timedelta_to_time(end_time - start_time))

            is_event = session.query(UserFreeEvent) \
                            .filter(UserFreeEvent.booking_request_id == request_id) \
                            .first()

            is_event = True if is_event != None else False

            user_name = userdao.get_user_name(uid)

            # 추가 업무로 인해 소요된 시간이 더 크다면 앞 뒤 일정을 고려.
            # 고려해서 이동이 가능하다면 추가 업무 할당함.
            if total_taking_time_in_minutes > org_taking_time_in_minutes:
                print '2'
                master_id, time = masterdao.get_masterid_and_starttime_from_booking(booking_id)
                search_key = '%s_%d' % (master_id, time)
                new_estimated_end_time = masterdao.is_schedule_extend_available(booking_id, total_taking_time_in_minutes)

                if new_estimated_end_time != None and holder.store(search_key, 1): # 변경이 가능함.
                    if payment_status == BC.BOOKING_PAID: # 미리 지불한 경우는 취소 하고 다시 결제함
                        # 전거래 취소 및 재결제
                        if not (is_event and appointment_index == 1):
                            print 'in this case'
                            cancel_ret_code, msg = cancel_payment(uid, booking_id, price_with_task, partial = '0')
                            if cancel_ret_code:

                                pay_ret_code, pay_msg = request_payment(uid, user_name, booking_id, new_price, appointment_type, status='UPDATED')
                                if pay_ret_code:
                                    row.tid = pay_msg
                                    row.payment_status = BC.BOOKING_PAID
                                else:
                                    row.payment_status = BC.BOOKING_PAYMENT_FAILED
                                    session.commit()
                                    session.close()
                                    self.set_status(Response.RESULT_OK)
                                    add_err_ko_message_to_response(ret, pay_msg)
                                    return
                        else: # 정기 1회 이벤트 일 때
                            print 'hahaha'
                            charge_amount = new_price - row.price
                            print charge_amount

                            if row.price_with_task != row.price: # 다르면
                                charge_amount = new_price - row.price_with_task

                            pay_ret_code, pay_msg = request_payment(uid, user_name, booking_id, charge_amount, appointment_type, status='UPDATED')
                            if pay_ret_code:
                                row.tid = pay_msg
                                row.payment_status = BC.BOOKING_PAID
                            else:
                                row.payment_status = BC.BOOKING_PAYMENT_FAILED
                                session.commit()
                                session.close()
                                self.set_status(Response.RESULT_OK)
                                add_err_ko_message_to_response(ret, pay_msg)
                                return


                    row.estimated_end_time = new_estimated_end_time
                    row.additional_task = additional_task
                    row.price_with_task = new_price
                    row.laundry_apply_all = laundry_apply_all

                    session.commit()
                    holder.remove(search_key)

                else:
                    print '3'
                    session.close()
                    self.set_status(Response.RESULT_OK)
                    add_err_message_to_response(ret, err_dict['err_hm_have_next_schedule'])

                    # 메모리에서 삭제
                    holder.remove(search_key)
                    return

            else: # 같거나 작은 경우는 바로 변경
                print '4'
                if payment_status == BC.BOOKING_PAID: # 미리 지불한 경우는 취소 하고 다시 결제함
                    # 전거래 취소 및 재결제
                    if not (is_event and appointment_index == 1):
                        cancel_ret_code, msg = cancel_payment(uid, booking_id, price_with_task, partial = '0')
                        if cancel_ret_code:
                            user_name = userdao.get_user_name(uid)
                            pay_ret_code, pay_msg = request_payment(uid, user_name, booking_id, new_price, appointment_type, status='UPDATED')
                            if pay_ret_code:
                                row.tid = pay_msg
                                row.payment_status = BC.BOOKING_PAID
                            else:
                                row.payment_status = BC.BOOKING_PAYMENT_FAILED
                                session.commit()
                                session.close()
                                self.set_status(Response.RESULT_OK)
                                add_err_ko_message_to_response(ret, pay_msg)
                                return
                    else:
                        if row.price_with_task != row.price: # 다르면
                            charge_amount = row.price_with_task - new_price
                            cancel_payment(uid, booking_id, charge_amount, partial = '0')


                row.additional_task     = additional_task
                row.estimated_end_time  = end_time + dt.timedelta(minutes = total_taking_time_in_minutes - org_taking_time_in_minutes)
                row.price_with_task     = new_price
                row.laundry_apply_all   = laundry_apply_all

            # 빨래의 경우는 시간 변경이 없으므로 마지막에 바로 적용
            # about laundry

            print '5'
            all_upcoming_bookings = session.query(Booking) \
                    .filter(Booking.request_id == request_id) \
                    .filter(Booking.cleaning_status == BC.BOOKING_UPCOMMING) \
                    .filter(Booking.appointment_index >= appointment_index) \
                    .all()

            if laundry_apply_all == 1: # 전체 선택
                for booking in all_upcoming_bookings:
                    bits = "{0:07b}".format(booking.additional_task)
                    if bits[4] == '0': # 빨래가 세팅되어 있다면
                        booking.additional_task += 4 # 빨래
                    booking.laundry_apply_all = laundry_apply_all

            elif laundry_apply_all == -2: # 선택 해제
                for booking in all_upcoming_bookings:
                    bits = "{0:07b}".format(booking.additional_task)
                    if bits[4] == '1': # 빨래가 세팅되어 있다면
                        booking.additional_task -= 4 # 빨래 제거
                    booking.laundry_apply_all = laundry_apply_all

            print '6'

            session.commit()

            # alim talk
            user_name = userdao.get_user_name(uid)
            additional_task_str = additional_task_string(additional_task)

            #for manager_phone in MANAGERS_CALL.split(','):
            #    send_alimtalk(manager_phone, 'noti_manager_modify_task', user_name, additional_task_str)

            # log to mixpanel
            mix.track(uid, 'update additional task', {'time' : dt.datetime.now(), 'booking_id' : booking_id, 'additional_task' : additional_task, 'new_price' : new_price, 'total_taking_time' : total_taking_time, 'laundry_apply_all' : laundry_apply_all})

            # log to mongo
            mongo_logger.debug('update additional task', extra = { 'user_id' : uid, 'booking_id' : booking_id, 'additional_task' : additional_task, 'new_price' : new_price, 'total_taking_time' : total_taking_time, 'laundry_apply_all' : laundry_apply_all})

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

        except NoResultFound, e:
            print_err_detail(e)
            session.close()
            self.set_status(Response.RESULT_OK)
            add_err_message_to_response(ret, err_dict['err_no_record'])
            return

        except MultipleResultsFound, e:
            print_err_detail(e)
            session.close()
            self.set_status(Response.RESULT_OK)
            add_err_message_to_response(ret, err_dict['err_multiple_record'])
            return

        except Exception, e:
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)
            mongo_logger.error('error update additional task', extra = {'user_id' : uid, 'err' : str(e)})

        finally:
            self.write(json.dumps(ret))
