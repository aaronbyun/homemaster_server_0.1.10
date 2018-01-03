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
from sqlalchemy import and_
from data.dao.masterdao import MasterDAO
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, Master, User, UserAddress, Promotion, UserCoupon
from utils.datetime_utils import convert_datetime_format, timedelta_to_time, time_to_minutes
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel

class MyBookingsDetailHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")

        booking_id  = self.get_argument('booking_id', '')

        ret = {}

        mongo_logger = get_mongo_logger()
        mix = get_mixpanel()

        try:
            booking_detail = {}
            session = Session()

            print booking_id

            try:
                row = session.query(Booking, Master, UserAddress, Promotion, UserCoupon) \
                            .join(Master, Booking.master_id == Master.id) \
                            .join(UserAddress, and_(Booking.user_id == UserAddress.user_id, Booking.addr_idx == UserAddress.user_addr_index)) \
                            .outerjoin(Promotion, Booking.id == Promotion.booking_id) \
                            .outerjoin(UserCoupon, Booking.id == UserCoupon.booking_id) \
                            .filter(Booking.id == booking_id) \
                            .one()

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

            tooktime = time_to_minutes(timedelta_to_time(row.Booking.estimated_end_time - row.Booking.start_time))

            if row.Booking.appointment_type == BC.ONE_TIME or row.Booking.appointment_type == BC.ONE_TIME_BUT_CONSIDERING:
                if row.Booking.is_dirty == 1:
                    tooktime -= 120

            masterdao = MasterDAO()
            master_name, master_img_url, master_rating = masterdao.get_master_name_img_and_average_rating(row.Master.id)

            booking_detail['id']                = row.Booking.id
            booking_detail['index']             = row.Booking.appointment_index
            booking_detail['havereview']        = row.Booking.havereview
            booking_detail['master_name']       = master_name
            booking_detail['master_img_url']    = master_img_url
            booking_detail['master_img_url']    = master_img_url
            booking_detail['master_rating']     = str(float(master_rating))
            booking_detail['size']              = row.UserAddress.size
            booking_detail['kind']              = row.UserAddress.kind
            booking_detail['datetime']          = convert_datetime_format(row.Booking.start_time)
            booking_detail['tooktime']          = int(tooktime / 6) # to make 2.5 to 25
            booking_detail['address_idx']       = row.Booking.addr_idx
            booking_detail['period']            = row.Booking.appointment_type
            booking_detail['additional_task']   = row.Booking.additional_task
            booking_detail['price']             = row.Booking.price
            booking_detail['actual_price']      = row.Booking.price_with_task
            booking_detail['card_idx']          = row.Booking.card_idx
            booking_detail['message']           = row.Booking.message
            booking_detail['cleaning_status']   = row.Booking.cleaning_status
            booking_detail['payment_status']    = row.Booking.payment_status

            booking_detail['promotion_applied'] = 1 if row.Promotion != None else 0
            booking_detail['coupon_applied']    = 1 if row.UserCoupon != None else 0

            discount_price = 0

            if row.UserCoupon != None:
                discount_price = row.UserCoupon.discount_price
                price = row.Booking.price_with_task

                if discount_price <= 100:
                    amount_discount_percent = 100 - discount_price
                    before_price = int(price * 100 / float(amount_discount_percent))
                    print 'before_price : ', before_price
                    discount_price = int(before_price * float(discount_price) / 100)
                    print 'discount_price : ', discount_price

            booking_detail['coupon_discount_price']  = discount_price

            #booking_detail['laundry_apply_all'] = row.Booking.laundry_apply_all


            start_time = row.Booking.start_time
            request_id = row.Booking.request_id

            next_start_time = session.query(Booking.start_time) \
                                    .filter(Booking.request_id == request_id) \
                                    .filter(Booking.start_time > start_time) \
                                    .order_by(Booking.start_time) \
                                    .first()


            if next_start_time != None:
                booking_detail['next_datetime']     = dt.datetime.strftime(next_start_time[0], '%Y%m%d %H%M')
            else:
                booking_detail['next_datetime']     = ''

            ret['response'] = booking_detail
            self.set_status(Response.RESULT_OK)

            user_id = row.Booking.user_id

            mix.track(user_id, 'got booking detail', {'time' : dt.datetime.now(), 'id' : row.Booking.id})
            mongo_logger.debug('got booking detail', extra = {'user_id' : user_id})

            print booking_id, 'successfully retrieved...by', user_id

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            print 'finalyy'
            session.close()
            self.write(json.dumps(ret))
