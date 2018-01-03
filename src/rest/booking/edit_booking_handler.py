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
from data.model.data_model import Booking
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

class EditBookingHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")

        booking_id              = self.get_argument('booking_id', '')
        changed                 = self.get_argument('ischange', '')
        date                    = self.get_argument('date', dt.datetime.now())
        start_time_range_begin  = self.get_argument('range_begin', BC.START_TIME_RANGE_BEGIN)
        start_time_range_begin_min  = self.get_argument('range_begin_min', 0)
        start_time_range_end    = self.get_argument('range_end',   BC.START_TIME_RANGE_END)
        start_time_range_end_min    = self.get_argument('range_end_min',   0)
        price                   = self.get_argument('price', 0)
        taking_time             = self.get_argument('taking_time', 25)
        additional_task         = self.get_argument('additional_task', 0)
        message                 = self.get_argument('msg', '')
        laundry_apply_all       = self.get_argument('laundry_apply_all', 0) # -1 - 없앰, 0 - one time, 1 - all time


        print 'edit booking params....'
        print booking_id, changed, date, additional_task, taking_time, price
        # convert datetime
        
        price                   = int(price)
        taking_time             = int(taking_time)
        additional_task         = int(additional_task)
        taking_time_in_minutes  = taking_time * 6 
        laundry_apply_all       = int(laundry_apply_all)

        changed = "{0:03b}".format(int(changed))

        mongo_logger = get_mongo_logger()

        mongo_logger.debug('%s was called to updated' % booking_id, extra = { 'changed' : changed,
                                                                      'date' : date,
                                                                      'start_time_range_begin' : start_time_range_begin,
                                                                      'start_time_range_end' : start_time_range_end,
                                                                        'price' : price,  
                                                                        'taking_time' : taking_time,
                                                                        'additional_task' : additional_task,
                                                                        'user_message' : message
                                                                        })

        ret = {}

        
        mix = get_mixpanel()

        try:
            session = Session()

            userdao = UserDAO()
            addrdao = AddressDAO()
            masterdao = MasterDAO()

            try:
                row = session.query(Booking).filter(Booking.id == booking_id).one()
            except NoResultFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_no_record'])
                return                

            except MultipleResultsFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_multiple_record'])
                return 
                

            uid           = row.user_id 
            price_with_task = row.price_with_task
            appointment_type = row.appointment_type
            org_master_id = row.master_id

            holder = IntermediateValueHolder()

            org_date = dt.datetime.strftime(row.start_time, '%m월%d일')

            time_changed = changed[2]
            task_changed = changed[1]
            msg_changed  = changed[0]

            # booking can not be updated within 24 hours ahead
            appointment_time = row.start_time
            current_time = dt.datetime.now()
            diff_in_hours = (appointment_time - current_time).total_seconds() / 3600

            if diff_in_hours < 24: # 못바꾸도록 함
                time_changed = 0
                task_changed = 0

            havetools = 1
            if additional_task >= 64:
                havetools = 0

            # time이 변경되었다면 무조건 scheduling 
            if time_changed == '1':
                date                    = dt.datetime.strptime(date, '%Y%m%d')
                start_time_range_begin  = int(start_time_range_begin)
                start_time_range_begin_min  = int(start_time_range_begin_min)
                start_time_range_end    = int(start_time_range_end) 
                start_time_range_end_min    = int(start_time_range_end_min) 

                
                appointment_type = 0 # 여기서는 1회 청소로 한다. 편집이기 때문에
                start_time       = row.start_time
                end_time         = row.estimated_end_time
                have_pet         = row.havepet
                master_gender    = row.master_gender
                price_with_task  = row.price_with_task 
                addr_idx         = row.addr_idx

                org_taking_time_in_minutes = time_to_minutes(timedelta_to_time(end_time - start_time))
                new_taking_time_in_minutes = org_taking_time_in_minutes + taking_time_in_minutes

                address, geohash5, geohash6 = userdao.get_user_address_by_index(uid, addr_idx)
                gu_id = addrdao.get_gu_id(address)
                dates = [int(dt.datetime.strftime(date, '%Y%m%d'))]

                schedule_by_date_list = masterdao.get_master_schedule_by_dates(gu_id, have_pet, master_gender, dates)
                success, msg, store_key, search_keys, result = masterdao.find_master_by_score(schedule_by_date_list, \
                                                    gu_id, \
                                                    uid, \
                                                    appointment_type, \
                                                    dates, \
                                                    start_time_range_begin, \
                                                    start_time_range_begin_min, \
                                                    start_time_range_end, \
                                                    start_time_range_end_min, \
                                                    new_taking_time_in_minutes, \
                                                    geohash6)

                # if not successful
                if success != 'SUCCESS':
                    session.close()
                    self.set_status(Response.RESULT_OK)
                    add_err_message_to_response(ret, err_dict['err_no_hm_at_that_time'])
                    self.write(json.dumps(ret)) 
                    return     

                else: # find matching homemaster
                    item = result[0]                    

                    master_id = item['mid']
                    dow                = dt.datetime.strptime(item['date'], '%Y%m%d').date().weekday()
                    start_time         = dt.datetime.combine(dt.datetime.strptime(item['date'], '%Y%m%d'), item['start_time'])
                    estimated_end_time = dt.datetime.combine(dt.datetime.strptime(item['date'], '%Y%m%d'), item['end_time'])

                    status = row.payment_status
                    if status == BC.BOOKING_PAID: # 미리 지불한 경우는 취소 하고 다시 결제함
                        # 전거래 취소 및 재결제
                        cancel_ret_code, msg = cancel_payment(uid, booking_id, price_with_task, partial = '0')
                        if cancel_ret_code:
                            user_name = userdao.get_user_name(uid)
                            pay_ret_code, pay_msg = request_payment(uid, user_name, booking_id, price, appointment_type, status='UPDATED')
                            if pay_ret_code:
                                row.tid = pay_msg
                                row.payment_status = BC.BOOKING_PAID
                            else:
                                row.payment_status = BC.BOOKING_PAYMENT_FAILED
                                session.commit()
                                session.close()
                                self.set_status(Response.RESULT_OK)
                                add_err_ko_message_to_response(ret, pay_msg)
                                self.write(json.dumps(ret)) 
                                return     

                    row.master_id = master_id
                    row.dow = dow
                    row.price_with_task = price
                    row.start_time = start_time
                    row.message = message
                    row.additional_task = additional_task
                    row.havetools = havetools
                    row.estimated_end_time = estimated_end_time
                    row.laundry_apply_all = laundry_apply_all

                    if org_master_id != master_id:
                        row.is_master_changed = 1


                    # about laundry
                    request_id = row.request_id
                    appointment_index = row.appointment_index

                    all_bookings = session.query(Booking) \
                            .filter(Booking.request_id == request_id) \
                            .filter(Booking.cleaning_status == BC.BOOKING_UPCOMMING) \
                            .filter(Booking.appointment_index > appointment_index) \
                            .all()

                    if laundry_apply_all == 1:
                        for booking in all_bookings:
                            booking.additional_task += 4 # 빨래
                            booking.laundry_apply_all = laundry_apply_all
                    else:
                        for booking in all_bookings:
                            bits = "{0:07b}".format(booking.additional_task)
                            if bits[4] == '1':
                                booking.additional_task -= 4 # 빨래 제거
                            booking.laundry_apply_all = laundry_apply_all

                    session.commit()

                    holder.remove(store_key)
                    for sk in search_keys:
                        holder.remove(sk)

            else:
                if task_changed == '1':
                    if taking_time_in_minutes > 0: # 실제 시간이 늘어났을 경우에만 뒷 스케쥴 확인

                        master_id, start_date_int = masterdao.get_masterid_and_starttime_from_booking(booking_id)
                        search_key = '%s_%d' % (master_id, start_date_int)

                        new_estimated_end_time = masterdao.is_master_available_next_schedule(booking_id, taking_time_in_minutes)
                        print new_estimated_end_time, '&&&&'

                        if new_estimated_end_time != None and holder.store(search_key, 1): # 실제로 시간이 가능하면
                            status = row.payment_status
                            if status == BC.BOOKING_PAID: # 미리 지불한 경우는 취소 하고 다시 결제함
                                # 전거래 취소 및 재결제
                                cancel_ret_code, msg = cancel_payment(uid, booking_id, price_with_task, partial = '0')
                                if cancel_ret_code:
                                    user_name = userdao.get_user_name(uid)
                                    pay_ret_code, pay_msg = request_payment(uid, user_name, booking_id, price, appointment_type, status='UPDATED')
                                    if pay_ret_code:
                                        row.tid = pay_msg
                                        row.payment_status = BC.BOOKING_PAID
                                    else:
                                        row.payment_status = BC.BOOKING_PAYMENT_FAILED
                                        session.commit()
                                        session.close()
                                        self.set_status(Response.RESULT_OK)
                                        add_err_ko_message_to_response(ret, pay_msg)
                                        self.write(json.dumps(ret)) 
                                        return     


                            row.estimated_end_time = new_estimated_end_time
                            row.additional_task = additional_task
                            row.message = message 
                            row.price_with_task = price
                            row.havetools = havetools
                            row.laundry_apply_all = laundry_apply_all

                            # about laundry
                            request_id = row.request_id
                            appointment_index = row.appointment_index

                            all_bookings = session.query(Booking) \
                                    .filter(Booking.request_id == request_id) \
                                    .filter(Booking.cleaning_status == BC.BOOKING_UPCOMMING) \
                                    .filter(Booking.appointment_index > appointment_index) \
                                    .all()

                            if laundry_apply_all == 1:
                                for booking in all_bookings:
                                    booking.additional_task += 4 # 빨래
                                    booking.laundry_apply_all = laundry_apply_all
                            else:
                                for booking in all_bookings:
                                    bits = "{0:07b}".format(booking.additional_task)
                                    if bits[4] == '1':
                                        booking.additional_task -= 4 # 빨래 제거
                                    booking.laundry_apply_all = laundry_apply_all

                            session.commit()

                            # 메모리에서 삭제
                            holder.remove(search_key)

                        else: # 스케쥴이 있어서 불가능 함                   
                            session.close()
                            self.set_status(Response.RESULT_OK)
                            add_err_message_to_response(ret, err_dict['err_hm_have_next_schedule'])
                            self.write(json.dumps(ret)) 
                            return     
                    else: # 시간이 줄어들었거나, 그대로인경우에는 additional task 값만 바꾸면 됨     
                        status = row.payment_status
                        if status == BC.BOOKING_PAID: # 미리 지불한 경우는 취소 하고 다시 결제함
                            # 전거래 취소 및 재결제
                            cancel_ret_code, msg = cancel_payment(uid, booking_id, price_with_task, partial = '0')
                            if cancel_ret_code:
                                user_name = userdao.get_user_name(uid)
                                pay_ret_code, pay_msg = request_payment(uid, user_name, booking_id, price, appointment_type, status='UPDATED')
                                if pay_ret_code:
                                    row.tid = pay_msg
                                    row.payment_status = BC.BOOKING_PAID
                                else:
                                    row.payment_status = BC.BOOKING_PAYMENT_FAILED
                                    session.commit()
                                    session.close()
                                    self.set_status(Response.RESULT_OK)
                                    add_err_ko_message_to_response(ret, pay_msg)
                                    self.write(json.dumps(ret)) 
                                    return    

                        print row.estimated_end_time, taking_time_in_minutes
                        row.estimated_end_time = row.estimated_end_time + dt.timedelta(minutes=taking_time_in_minutes)      
                        row.additional_task = additional_task
                        row.message = message
                        row.price_with_task = price
                        row.havetools = havetools
                        row.laundry_apply_all = laundry_apply_all

                        # about laundry
                        request_id = row.request_id
                        appointment_index = row.appointment_index

                        all_bookings = session.query(Booking) \
                                .filter(Booking.request_id == request_id) \
                                .filter(Booking.cleaning_status == BC.BOOKING_UPCOMMING) \
                                .filter(Booking.appointment_index > appointment_index) \
                                .all()

                        if laundry_apply_all == 1:
                            for booking in all_bookings:
                                booking.additional_task += 4 # 빨래
                                booking.laundry_apply_all = laundry_apply_all
                        else:
                            for booking in all_bookings:
                                bits = "{0:07b}".format(booking.additional_task)
                                if bits[4] == '1':
                                    booking.additional_task -= 4 # 빨래 제거
                                booking.laundry_apply_all = laundry_apply_all

                        session.commit()
                else:
                    row.message = message
                    session.commit()

            # 문자 전송 
            #send_updated_text(booking_id, org_date) 

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

            mix.track(uid, 'update', {'time' : dt.datetime.now(), 'booking_id' : booking_id, 'additional_task' : additional_task})
            mongo_logger.debug('%s was updated' % booking_id, extra = {'user_id' : uid, 'booking_id' : booking_id})
            print booking_id, 'successfully updated...'

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
            mongo_logger.error('error occurred when updating booking', extra = {'err' : str(e)})

        finally:
            session.close()
            self.write(json.dumps(ret))