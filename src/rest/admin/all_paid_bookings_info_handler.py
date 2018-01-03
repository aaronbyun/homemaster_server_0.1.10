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
from sqlalchemy import and_
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, UserPaymentRecord, User, UserAddress, Master, Promotion, EventPromotionBooking
from data.dao.userdao import UserDAO
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.encryption import aes_helper as aes
from sqlalchemy import desc

class AllPaidBookingInfoHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        try:
            session = Session()

            bookings = []

            result = session.query(UserPaymentRecord, Booking, Promotion, EventPromotionBooking, Master, User, UserAddress) \
                            .join(Booking, Booking.id == UserPaymentRecord.booking_id) \
                            .outerjoin(Promotion, Booking.id == Promotion.booking_id) \
                            .outerjoin(EventPromotionBooking, Booking.id == EventPromotionBooking.booking_id) \
                            .join(Master, Master.id == Booking.master_id) \
                            .join(User, Booking.user_id == User.id) \
                            .join(UserAddress, and_(Booking.user_id == UserAddress.user_id, Booking.addr_idx == UserAddress.user_addr_index)) \
                            .order_by(desc(UserPaymentRecord.auth_date)) \
                            .all()
                            
            for row in result:

                userdao = UserDAO()
                key = userdao.get_user_salt_by_id(row.User.id)[:16]
                crypto = aes.MyCrypto(key)

                booking_info = {}
                booking_info['booking_id']          = row.Booking.id
                booking_info['request_id']          = row.Booking.request_id
                booking_info['authdate']            = row.UserPaymentRecord.auth_date
                booking_info['master_gender']       = row.Booking.master_gender
                booking_info['master_name']         = row.Master.name
                booking_info['user_id']             = row.User.id
                booking_info['user_name']           = crypto.decodeAES(row.User.name)
                booking_info['user_email']          = row.User.email
                booking_info['user_gender']         = row.User.gender
                booking_info['user_phone']          = crypto.decodeAES(row.User.phone)
                booking_info['user_address']        = crypto.decodeAES(row.UserAddress.address)
                booking_info['user_home_size']      = row.UserAddress.size
                booking_info['user_home_kind']      = row.UserAddress.kind
                booking_info['devicetype']          = row.User.devicetype
                booking_info['appointment_type']    = row.Booking.appointment_type
                booking_info['appointment_index']   = row.Booking.appointment_index
                booking_info['start_time']          = dt.datetime.strftime(row.Booking.start_time, '%Y-%m-%d %H:%M')
                booking_info['estimated_end_time']  = dt.datetime.strftime(row.Booking.estimated_end_time, '%Y-%m-%d %H:%M')
                booking_info['additional_task']     = row.Booking.additional_task
                booking_info['promotion_code']      = row.Promotion.promotion_code if row.Promotion != None else 'No code'
                booking_info['promotion_amount']    = row.Promotion.discount_price if row.Promotion != None else '0'
                booking_info['event_promotion_code']      = row.EventPromotionBooking.event_name if row.EventPromotionBooking != None else 'No event code'
                booking_info['event_promotion_amount']    = row.EventPromotionBooking.discount_price if row.EventPromotionBooking != None else '0'
                booking_info['price']               = row.UserPaymentRecord.price
                booking_info['msg']                 = row.Booking.message if row.Booking.message != None else ''
                booking_info['trash_location']      = row.Booking.trash_location if row.Booking.trash_location != None else ''
                booking_info['enterhome']           = crypto.decodeAES(row.Booking.enterhome) if row.Booking.enterhome != None else ''
                booking_info['enterbuilding']       = crypto.decodeAES(row.Booking.enterbuilding) if row.Booking.enterbuilding != None else ''
                booking_info['havepet']             = row.Booking.havepet
                booking_info['status']              = row.UserPaymentRecord.status                            

                bookings.append(booking_info)


            ret['response'] = bookings
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))