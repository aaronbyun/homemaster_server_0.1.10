#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import datetime as dt

from sqlalchemy import and_, or_, func
from rest.booking import booking_constant as BC
from err.error_handler import print_err_detail
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, UserPaymentRecord, CancelReason
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from data.encryption import aes_helper as aes

class BookingDAO(object):
    def __init__(self):
        pass

    def is_inner_booking(self, auth_source):
        result = False

        if auth_source == '' or auth_source == 'None' or auth_source == 'FB':
            result = True

        return result


    def is_next_booking_left_over_2days(self, booking_id):
        try:
            session = Session()
            stmt = session.query(Booking) \
                          .filter(Booking.id == booking_id) \
                          .one()

            booking_request_id = stmt.request_id
            booking_start_time = stmt.start_time

            next_booking = session.query(Booking) \
                                    .filter(Booking.request_id == booking_request_id) \
                                    .filter(Booking.start_time > booking_start_time) \
                                    .filter(Booking.cleaning_status == BC.BOOKING_UPCOMMING) \
                                    .order_by(Booking.start_time) \
                                    .first()

            print next_booking
            if next_booking == None:
                return 'SUCCESS', True, -1

            now = dt.datetime.now().date()
            upcoming_booking_time = next_booking.start_time.date()

            diff = (upcoming_booking_time - now).days
            if  diff >= 3:
                return 'SUCCESS', True, diff

            return 'SUCCESS', True, diff
        except Exception, e:
            print e
            return 'FAILURE', '', 0
        finally:
            session.close()

    def cancel_all_upcomings(self, booking_id):
        try:
            session = Session()
            stmt = session.query(Booking) \
                          .filter(Booking.id == booking_id) \
                          .one()

            booking_request_id = stmt.request_id
            booking_start_time = stmt.start_time

            result = session.query(Booking) \
                            .filter(Booking.request_id == booking_request_id) \
                            .filter(Booking.start_time > booking_start_time) \
                            .filter(Booking.cleaning_status == BC.BOOKING_UPCOMMING) \
                            .order_by(Booking.start_time) \
                            .all()

            for row in result:
                row.cleaning_status = BC.BOOKING_CANCELED

            session.commit()
            return 'SUCCESS'
        except Exception, e:
            print e
            return 'FAILURE'
        finally:
            session.close()


    def get_cancel_reason(self, booking_id):
        reason = ''

        cancel_reasons = []
        cancel_reasons.append('지금은 서비스가 필요하지 않아요')
        cancel_reasons.append('집에 없어서 문을 열어드릴 수가 없어요')
        cancel_reasons.append('시간이 마음에 들지 않아요')
        cancel_reasons.append('클리닝을 잊고 있었네요')
        cancel_reasons.append('원하는 홈마스터가 아니에요')
        cancel_reasons.append('기타')
        cancel_reasons.append('관리자가 취소 했습니다')

        cancel_all_reasons = []
        cancel_all_reasons.append('너무 비싸요')
        cancel_all_reasons.append('제가 여행을 가요')
        cancel_all_reasons.append('청소품질이 마음에 들지 않아요')
        cancel_all_reasons.append('필요할 때에만 서비스를 이용하고 싶어요')
        cancel_all_reasons.append('다른 업체로 바꿀래요')
        cancel_all_reasons.append('원하던 홈마스터가 오질 않아요')
        cancel_all_reasons.append('저 이사가요')
        cancel_all_reasons.append('기타')
        cancel_all_reasons.append('관리자가 취소 했습니다')

        try:
            session = Session()
            row = session.query(CancelReason).filter(CancelReason.booking_id == booking_id).one()

            kind = row.kind
            index = row.reason_id
            etc = row.etc_reason

            if kind == 0: # cancel
                reason = cancel_reasons[index]
            else:
                reason = cancel_all_reasons[index]

            if reason == '기타':
                reason += ' ' + etc
        except Exception, e:
            print e
            reason = ''
        finally:
            return reason

    def get_extra_charge(self, booking_id):
        extra_charge = 0

        try:
            session = Session()
            row = session.query(func.ifnull(func.sum(UserPaymentRecord.price), 0)) \
                        .filter(UserPaymentRecord.booking_id == booking_id) \
                        .filter(UserPaymentRecord.status == 'CHARGED') \
                        .one()

            extra_charge = int(row[0]) * 0.8
            extra_charge = int(extra_charge)

        except Exception, e:
            print e
            extra_charge = 0

        finally:
            session.close()
            return int(extra_charge)


if __name__ == '__main__':
    dao = BookingDAO()
    print dao.get_cancel_reason('VgmA4dr1nmkBAeLG')
