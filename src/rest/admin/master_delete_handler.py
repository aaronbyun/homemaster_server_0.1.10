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
from sqlalchemy import func, and_, or_
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from data.session.mysql_session import engine, Session
from data.model.data_model import Master, MasterTimeSlot, Booking, UserAddress, User
from data.dao.masterdao import MasterDAO
from data.dao.addressdao import AddressDAO
from data.dao.userdao import UserDAO
from data.encryption import aes_helper as aes
from utils.datetime_utils import convert_datetime_format, time_to_minutes, timedelta_to_time
from rest.booking import booking_constant as BC
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.intermediate.value_holder import IntermediateValueHolder

class MasterDeleteHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")

        master_id   = self.get_argument('master_id', '')
        
        ret = {}

        # 해당 마스터의 상태를 deactivate 시킨다.
        # 남아있는 일정이 있다면 모든 일정을 다른 마스터에게 양도 한다.

        try:
            session = Session()

            userdao = UserDAO()
            addrdao = AddressDAO()
            masterdao = MasterDAO()

            holder = IntermediateValueHolder()

            # deactivate master
            row = session.query(Master).filter(Master.id == master_id).one()
            row.active = 0
            session.commit()

            # automatically assign that master's remain jobs to other masters
            masterdao = MasterDAO()
            request_ids = masterdao.get_distinct_req_ids(master_id)

            matched_booking_groups = []
            unmatched_booking_groups = []

            for req_id in request_ids:
                reqs = session.query(Booking, User, UserAddress) \
                    .join(User, User.id == Booking.user_id) \
                    .join(UserAddress, and_(Booking.user_id == UserAddress.user_id, Booking.addr_idx == UserAddress.user_addr_index)) \
                    .filter(Booking.request_id == req_id).filter(Booking.cleaning_status == BC.BOOKING_UPCOMMING) \
                    .order_by(Booking.start_time) \
                    .all()

                key = userdao.get_user_salt_by_id(reqs.User.id)[:16]
                crypto = aes.MyCrypto(key)

                dates = []
                datetimes = []
                max_taking_time_in_minutes = 0
                for item in reqs:
                    appointment_type = item.Booking.appointment_type
                    address = crypto.decodeAES(item.UserAddress.address)
                    geohash5 = item.UserAddress.geohash5
                    geohash6 = item.UserAddress.geohash6
                    start_time = item.Booking.start_time
                    end_time  = item.Booking.estimated_end_time

                    # 최대 시간 기준으로 할당을 잡음
                    taking_time_in_minutes = time_to_minutes(timedelta_to_time(end_time - start_time))
                    if taking_time_in_minutes > max_taking_time_in_minutes:
                        max_taking_time_in_minutes = taking_time_in_minutes

                    gu_id = addrdao.get_gu_id(address)
                    dates.append( int(dt.datetime.strftime(start_time, '%Y%m%d')))

                    datetimes.append(start_time)

                uid = item.Booking.user_id
                time_range_begin = datetimes[0].hour
                time_range_begin_min = datetimes[0].minute
                time_range_end = datetimes[0].hour
                time_range_end_min = datetimes[0].minute
                have_pet = item.Booking.havepet
                master_gedner = item.Booking.master_gender

                schedule_by_date_list = masterdao.get_master_schedule_by_dates(gu_id, have_pet, master_gender, dates)
                success, msg, store_key, search_keys, result = masterdao.find_master_by_score(schedule_by_date_list, \
                                                    gu_id, \
                                                    uid, \
                                                    appointment_type, \
                                                    dates, \
                                                    time_range_begin, \
                                                    time_range_begin_min, \
                                                    time_range_end, \
                                                    time_range_end_min, \
                                                    max_taking_time_in_minutes, \
                                                    geohash6)

                if success == 'SUCCESS':
                    matched_booking_groups.append(req_id)

                    matched_list = session.query(Booking) \
                                        .filter(Booking.request_id == req_id) \
                                        .filter(Booking.cleaning_status == BC.BOOKING_UPCOMMING) \
                                        .all()

                    for match in matched_list:
                        match.master_id = result[0]['mid']

                    session.commit()

                    holder.remove(store_key)
                    for sk in search_keys:
                        holder.remove(sk)

                else:
                    unmatched_booking_groups.append(req_id)

                    unmatched_list = session.query(Booking) \
                                        .filter(Booking.request_id == req_id) \
                                        .filter(Booking.cleaning_status == BC.BOOKING_UPCOMMING) \
                                        .all()


                    for unmatch in unmatched_list:
                        print unmatch
                        unmatch.master_id = None

                    session.commit()

            ret['response'] = {'matched_group' : matched_booking_groups, 'unmatched_group' : unmatched_booking_groups}
            self.set_status(Response.RESULT_OK)

        except NoResultFound, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_no_record'])            

        except MultipleResultsFound, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_multiple_record'])            

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()
            self.write(json.dumps(ret))
