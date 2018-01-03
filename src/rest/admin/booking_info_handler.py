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
from sqlalchemy import and_, desc
from rest.booking import booking_constant as BC
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, Master, User, UserAddress, Rating, MasterMemo, OrderID11st
from data.dao.userdao import UserDAO
from data.encryption import aes_helper as aes
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from utils.address_utils import convert_to_jibun_address


class BookingInfoHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        booking_id = self.get_argument('booking_id', '')

        ret = {}

        try:
            session = Session()

            row = session.query(Booking, Rating, OrderID11st, Master, User, UserAddress, MasterMemo) \
                        .outerjoin(Rating, Booking.id == Rating.booking_id) \
                        .outerjoin(OrderID11st, Booking.id == OrderID11st.booking_id) \
                        .join(Master, Booking.master_id == Master.id) \
                        .join(User, Booking.user_id == User.id) \
                        .join(UserAddress, and_(Booking.user_id == UserAddress.user_id, Booking.addr_idx == UserAddress.user_addr_index)) \
                        .outerjoin(MasterMemo, Booking.user_id == MasterMemo.user_id) \
                        .filter(Booking.id == booking_id) \
                        .order_by(desc(MasterMemo.datetime)) \
                        .first()

            if row == None: # no entry
                session.close()
                add_err_message_to_response(ret, err_dict['err_no_entry_to_cancel'])
                self.write(json.dumps(ret))
                return

            userdao = UserDAO()
            key = userdao.get_user_salt_by_id(row.User.id)[:16]
            crypto = aes.MyCrypto(key)

            estimated_end_time = row.Booking.estimated_end_time
            if row.Booking.appointment_type == BC.ONE_TIME or row.Booking.appointment_type == BC.ONE_TIME_BUT_CONSIDERING:
                if row.Booking.is_dirty == 1:
                    estimated_end_time -= dt.timedelta(hours=2)

            appointment_index   = row.Booking.appointment_index
            appointment_type    = row.Booking.appointment_type
            start_time          = row.Booking.start_time
            end_time            = row.Booking.estimated_end_time
            cleaning_duration   = row.Booking.cleaning_duration / 6
            is_dirty            = row.Booking.is_dirty
            is_b2b              = row.User.is_b2b

            duration_in_minutes = (end_time - start_time).seconds / 360 # 계산을 단순하게 하기 위해 60 * 60이 아닌 60 * 6으로 나눔. 그뒤 10배 커지는 것을 방지하기 위해 시급에서 10 나눈 값만 곱함
            minutes_for_salary = duration_in_minutes

            #if duration_in_minutes > cleaning_duration: # 30분의 시간이 더 더해지는 경우가 존재. 그 경우, 해당 시간은 임금에 반영 되지 않음
            #    if appointment_index == 1 and (appointment_type == BC.ONE_TIME_A_MONTH or appointment_type == BC.TWO_TIME_A_MONTH or appointment_type == BC.FOUR_TIME_A_MONTH):
            #        minutes_for_salary = duration_in_minutes - 5

            if is_dirty == 1:
                minutes_for_salary -= 20

            house_type = row.UserAddress.kind
            house_size = row.UserAddress.size

            expected_salary = 0

            if is_b2b:
                expected_salary = int(minutes_for_salary * (row.Booking.wage_per_hour / 10))
            else:
                if start_time >= dt.datetime(2017, 1, 1):
                    expected_salary = minutes_for_salary * BC.SALARY_FOR_ONETIME_IN_HOUR
                else:
                    if appointment_type in BC.REGULAR_CLEANING_DICT:
                        expected_salary = minutes_for_salary * BC.SALARY_FOR_REGULAR_IN_HOUR
                    else:
                        expected_salary = minutes_for_salary * BC.SALARY_FOR_ONETIME_IN_HOUR

                if start_time.weekday() in BC.WEEKEND and start_time >= dt.datetime(2016, 12, 17):
                    expected_salary += BC.WEEKEND_ADDED_SALARY

            booking_info = {}
            booking_info['booking_id']          = row.Booking.id
            booking_info['request_id']          = row.Booking.request_id
            booking_info['master_gender']       = row.Booking.master_gender
            booking_info['master_name']         = row.Master.name
            booking_info['master_pet_alergy']   = row.Master.pet_alergy

            booking_info['user_memo']           = row.MasterMemo.memo if row.MasterMemo != None else ''
            booking_info['user_id']             = row.User.id
            booking_info['user_name']           = crypto.decodeAES(row.User.name)
            booking_info['user_email']          = row.User.email
            booking_info['user_gender']         = row.User.gender
            booking_info['user_phone']          = crypto.decodeAES(row.User.phone)
            booking_info['user_address']        = crypto.decodeAES(row.UserAddress.address)
            booking_info['jibun_address']       = convert_to_jibun_address(booking_info['user_address'])
            booking_info['user_home_size']      = row.UserAddress.size
            booking_info['user_home_kind']      = row.UserAddress.kind
            booking_info['devicetype']          = row.User.devicetype
            booking_info['appointment_type']    = row.Booking.appointment_type
            #booking_info['appointment_index']   = row.Booking.appointment_index
            booking_info['avg_rating']          = str( float((row.Rating.rate_clean + row.Rating.rate_master)) / 2.0) if row.Rating != None else 'None'
            booking_info['clean_review']        = row.Rating.review_clean if row.Rating != None else ''
            booking_info['master_review']       = row.Rating.review_master if row.Rating != None else ''
            booking_info['start_time']          = dt.datetime.strftime(row.Booking.start_time, '%Y-%m-%d %H:%M')
            booking_info['estimated_end_time']  = dt.datetime.strftime(estimated_end_time, '%Y-%m-%d %H:%M')
            booking_info['additional_task']     = row.Booking.additional_task
            booking_info['price']               = row.Booking.price_with_task
            booking_info['salary']              = expected_salary
            booking_info['msg']                 = row.Booking.message if row.Booking.message != None else ''
            booking_info['trash_location']      = row.Booking.trash_location if row.Booking.trash_location != None else ''
            booking_info['enterhome']           = crypto.decodeAES(row.Booking.enterhome) if row.Booking.enterhome != None else ''
            booking_info['enterbuilding']       = crypto.decodeAES(row.Booking.enterbuilding) if row.Booking.enterbuilding != None else ''
            #booking_info['havetools']           = row.Booking.havetools
            booking_info['havepet']             = row.Booking.havepet
            booking_info['status']              = row.Booking.status
            booking_info['payment_status']      = row.Booking.payment_status
            booking_info['cleaning_status']     = row.Booking.cleaning_status
            booking_info['routing_method']      = row.Booking.routing_method if row.Booking.routing_method != None else ''

            booking_info['is_b2b']              = is_b2b
            booking_info['11st_id']              = row.OrderID11st.div_no if row.OrderID11st != None else ''

            ret['response'] = booking_info
            self.set_status(Response.RESULT_OK)

            #print booking_info['enterhome']
            #print booking_info['enterbuilding']

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))
