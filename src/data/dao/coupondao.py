#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')


import datetime as dt
import rest.booking.booking_constant as BC

from sqlalchemy import and_

from err.error_handler import print_err_detail


from data.session.mysql_session import engine, Session
from data.model.data_model import UserCoupon, Booking
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

try:
    from utils.stipulation_text import PROMOTION_CODES
except ImportError:
    PROMOTION_CODES = ['']

class CouponDAO(object):
    def __init__(self):
        pass

    def cancel_coupon_usage(self, booking_id):
        session = Session()

        try:
            record = session.query(UserCoupon) \
                            .filter(UserCoupon.booking_id == booking_id) \
                            .first()
            if record:
                record.used = 0
                record.booking_id = None
                record.service_price = 0
                session.commit()

        except Exception, e:
            session.rollback()
            print_err_detail(e)

        finally:
            session.close()


    def cancelall_coupon_usage(self, booking_id):
        session = Session()

        try:
            booking_record = session.query(Booking).filter(Booking.id == booking_id).one()
            request_id = booking_record.request_id

            records = session.query(Booking) \
                            .filter(Booking.request_id == request_id) \
                            .filter(Booking.cleaning_status == BC.BOOKING_UPCOMMING) \
                            .all()
            for record in records:
                bid = record.id
                coupon_record = session.query(UserCoupon).filter(UserCoupon.booking_id == bid).first()

                if coupon_record:
                    coupon_record.used = 0
                    coupon_record.booking_id = None
                    coupon_record.service_price = 0
                    session.commit()

        except Exception, e:
            session.rollback()
            print_err_detail(e)

        finally:
            session.close()


    def set_coupon_status(self, coupon_id, status, booking_id, actual_price):
        result = True
        try:
            session = Session()
            row = session.query(UserCoupon) \
                        .filter(UserCoupon.id == coupon_id) \
                        .one()

            row.used = status
            row.booking_id = booking_id
            row.service_price = actual_price
            row.used_datetime = dt.datetime.now()

            session.commit()

        except Exception, e:
            print_err_detail(e)
            result = False

        finally:
            session.close()
            return result


if __name__ == '__main__':
    pass
