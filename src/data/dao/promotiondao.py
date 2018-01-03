#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')


import datetime as dt

from sqlalchemy import and_

from err.error_handler import print_err_detail

from data.session.mysql_session import engine, Session
from data.model.data_model import Promotion, EventPromotionBooking, EventPromotion
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

try:
    from utils.stipulation_text import PROMOTION_CODES
except ImportError:
    PROMOTION_CODES = ['']

class PromotionDAO(object):
    def __init__(self):
        pass

    def get_discount_price(self, promotion_code):
        discount_price = 0
        try:
            session = Session()
            row = session.query(Promotion).filter(Promotion.promotion_code == promotion_code).one()

            discount_price = row.discount_price

        except Exception, e:
            print_err_detail(e)
        finally:
            session.close()
            return discount_price

    def set_promotion_code_status(self, code, new_status, booking_id, price):
        UNUSED      = 0
        USED        = 1
        OCCUPIED    = 2

        try:
            session = Session()

            if code in PROMOTION_CODES:
                booking = session.query(EventPromotion).filter(EventPromotion.code == code).one()
                discount_price = booking.amount
                if discount_price <= 100: # 100 이하면 퍼센트로 간주
                    discount_price = price * discount_price

                eventpromotion_booking = EventPromotionBooking(booking_id = booking_id, event_name = code, discount_price = discount_price)
                session.add(eventpromotion_booking)

            else:
                try:
                    row = session.query(Promotion).filter(Promotion.promotion_code == code).one()
                except NoResultFound, e:
                    session.close()
                    print_err_detail(e)
                    return

                if new_status == USED:
                    row.used = new_status
                    row.booking_id = booking_id
                    row.service_price = price
                    row.used_datetime = dt.datetime.now()
                elif new_status  == UNUSED:
                    row.used = new_status

            session.commit()
        except Exception, e:
            print_err_detail(e)
        finally:
            session.close()

if __name__ == '__main__':
    pass
