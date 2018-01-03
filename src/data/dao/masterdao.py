#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import geohash
import datetime as dt
import copy
import numpy as np
from sqlalchemy import func, Date, cast
from sqlalchemy.orm import aliased
from sqlalchemy import and_, or_, func, desc
from rest.booking import booking_constant as BC
from itertools import groupby

from utils.datetime_utils import timedelta_to_time, time_to_minutes, time_added_minute, time_substracted_minute, convert_datetime_format2
from utils.geo_utils import get_moving_time

from err.error_handler import print_err_detail

from data.intermediate.value_holder import IntermediateValueHolder
from data.session.mysql_session import engine, Session
from data.model.data_model import MasterScheduleByDate, MasterPreferedArea, MasterTimeSlot, Master, Manager, Booking, UserAddress, MasterScheduleByDate, Rating, MasterSalary, Sigungu, MasterDeficiency, MasterPushKey, MasterBookingModifyRequest, MasterAccount
from data.encryption import aes_helper as aes
from userdao import UserDAO

class MasterDAO(object):
    def __init__(self):
        pass

    def get_all_master_ids(self):
        master_ids = []

        try:
            session = Session()
            result = session.query(Master).filter(Master.active != 0).order_by(Master.name).all()

            for row in result:
                master_ids.append(row.id)

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()
            return master_ids

    def is_unassigned(self, mid):
        valid = False

        try:
            session = Session()
            row = session.query(Master) \
                        .filter(Master.active == 2) \
                        .filter(Master.id == mid) \
                        .count()

            if row == 1:
                valid = True

        except Exception, e:
            print_err_detail(e)
            valid = False

        finally:
            session.close()
            return valid


    def is_valid_master(self, mid):
        valid = False
        try:
            session = Session()
            row = session.query(Master) \
                        .filter(Master.active == 1) \
                        .filter(Master.id == mid) \
                        .count()

            if row == 1:
                valid = True

        except Exception, e:
            print_err_detail(e)
            valid = False

        finally:
            session.close()
            return valid

    def get_master_completed_cleaning_count_at_date(self, mid, current_date):
        completed_cleaning_count = 0
        tmp_current_date = current_date + dt.timedelta(hours=23)

        try:
            session = Session()
            completed_cleaning_count = session.query(Booking) \
                                              .filter(Booking.master_id == mid) \
                                              .filter(Booking.cleaning_status == BC.BOOKING_COMPLETED) \
                                              .filter(Booking.start_time <= tmp_current_date) \
                                              .count()

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()
            return completed_cleaning_count


    def get_master_working_start_date(self, mid):
        working_startdate = ''

        try:
            session = Session()
            row = session.query(Booking) \
                            .filter(Booking.master_id == mid) \
                            .filter(Booking.cleaning_status > BC.BOOKING_CANCELED) \
                            .order_by(Booking.start_time) \
                            .first()

            if row == None:
                working_startdate = '없음'
            else:
                working_startdate = convert_datetime_format2(row.start_time)

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()
            return working_startdate

    def get_master_completed_cleaning_count(self, mid):
        completed_cleaning_count = 0

        try:
            session = Session()
            completed_cleaning_count = session.query(Booking) \
                            .filter(Booking.master_id == mid) \
                            .filter(Booking.cleaning_status == BC.BOOKING_COMPLETED) \
                            .count()

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()
            return completed_cleaning_count

    def get_master_ids_where_regions_available(self, sigungu):
        master_ids = []

        try:
            session = Session()
            result = session.query(Master, MasterPreferedArea, Sigungu) \
                            .join(MasterPreferedArea, Master.id == MasterPreferedArea.master_id) \
                            .join(Sigungu, MasterPreferedArea.prefered_gu == Sigungu.id) \
                            .filter(Master.active == 1) \
                            .filter(Sigungu.name.like('%'+sigungu+'%')) \
                            .order_by(Master.name) \
                            .all()

            for row in result:
                master_ids.append(row.Master.id)

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()
            return master_ids

    def get_master_name(self, mid):
        master_name = ''

        try:
            session = Session()
            result = session.query(Master).filter(Master.id == mid).one()
            master_name = result.name

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()
            return master_name


    def get_master_account(self, mid):
        bank_name = ''
        bank_code = ''
        account_no = ''

        try:
            session = Session()
            result = session.query(MasterAccount) \
                            .filter(MasterAccount.master_id == mid) \
                            .order_by(desc(MasterAccount.datetime)) \
                            .first()

            bank_name = result.bank_name
            bank_code = result.bank_code
            account_no = result.account_no

        except Exception, e:
            #print_err_detail(e)
            bank_name = ''
            bank_code = ''
            account_no = ''

        finally:
            session.close()
            return bank_name, bank_code, account_no


    def get_master_pushkey(self, mid):
        key = ''

        try:
            session = Session()
            result = session.query(Master, MasterPushKey) \
                            .outerjoin(MasterPushKey, Master.id == MasterPushKey.master_id) \
                            .filter(Master.id == mid).one()

            key = result.MasterPushKey.pushkey if result.MasterPushKey != None else ''

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()
            return key


    def get_master_phone(self, mid):
        master_phone = ''

        try:
            session = Session()
            result = session.query(Master).filter(Master.id == mid).one()
            master_phone = result.phone

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()
            return master_phone

    def get_master_basic_info(self, master_id):
        master_info = {}

        try:
            session = Session()
            row = session.query(Master, Manager) \
                            .join(Manager, Master.manager_id == Manager.id) \
                            .filter(Master.id == master_id) \
                            .one()

            master_info['name']         = row.Master.name
            master_info['phone']        = row.Master.phone
            master_info['img']          = row.Master.img_url
            master_info['age']          = row.Master.age
            master_info['gender']       = row.Master.gender
            master_info['address']      = row.Master.address
            master_info['manager_id']   = row.Manager.id
            master_info['manager_name'] = row.Manager.name
            master_info['manager_phone'] = row.Manager.phone
            master_info['cardinal']     = row.Master.cardinal
            master_info['level']        = row.Master.level
            master_info['pet_alergy']   = row.Master.pet_alergy
            master_info['active']       = row.Master.active
            master_info['need_route']   = row.Master.need_route
            master_info['t_size']       = row.Master.t_size

        except Exception, e:
            print 'master id :', master_id
            print_err_detail(e)

        finally:
            session.close()
            return master_info


    def get_master_prefered_area_count(self, master_id):
        prefered_area_count = 0
        try:
            session = Session()
            prefered_area_count = session.query(MasterPreferedArea) \
                            .filter(MasterPreferedArea.master_id == master_id) \
                            .count()

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()
            return prefered_area_count


    def get_master_penalties(self, master_id, start_period, end_period):
        penalty_amount = 0
        try:
            session = Session()

            former_start_period = start_period - dt.timedelta(days=7)
            former_end_period = end_period - dt.timedelta(days=7)

            former_start_month = former_start_period.month
            former_end_month = former_end_period.month
            start_month     = start_period.month
            end_month       = end_period.month

            if former_end_month == end_month:
                result = session.query(func.count(MasterBookingModifyRequest)) \
                                .filter(MasterBookingModifyRequest.master_id == master_id) \
                                .filter(func.month(MasterBookingModifyRequest.request_time) == end_month ) \
                                .filter(func.date(MasterBookingModifyRequest.request_time) <= former_end_period) \
                                .one()

                former_week_accumulated_count = result[0]

                result = session.query(func.count(MasterBookingModifyRequest)) \
                                .filter(MasterBookingModifyRequest.master_id == master_id) \
                                .filter(func.month(MasterBookingModifyRequest.request_time) == end_month) \
                                .filter(func.date(MasterBookingModifyRequest.request_time) <= end_period) \
                                .one()

                this_week_accumulated_count = result[0]
            else:
                result = session.query(func.count(MasterBookingModifyRequest)) \
                                .filter(MasterBookingModifyRequest.master_id == master_id) \
                                .filter(func.month(MasterBookingModifyRequest.request_time) == end_month -1) \
                                .filter(func.date(MasterBookingModifyRequest.request_time) <= former_end_period) \
                                .one()

                former_week_accumulated_count = result[0]

                result = session.query(func.count(MasterBookingModifyRequest)) \
                                .filter(MasterBookingModifyRequest.master_id == master_id) \
                                .filter(func.month(MasterBookingModifyRequest.request_time) == end_month - 1) \
                                .filter(func.date(MasterBookingModifyRequest.request_time) < end_period) \
                                .one()

                this_week_accumulated_count = result[0]

            # 내역 계산
            print former_week_accumulated_count, this_week_accumulated_count
            if former_week_accumulated_count > 2:
                if former_start_month == start_month:
                    penalty_amount = this_week_accumulated_count - former_week_accumulated_count
                else:
                    penalty_amount = this_week_accumulated_count - 2

            else:
                if this_week_accumulated_count > 2:
                    penalty_amount = this_week_accumulated_count - 2
            # 건당 2만원
            penalty_amount = penalty_amount * 20000

        except Exception, e:
            print_err_detail(e)
        finally:
            session.close()
            return penalty_amount


    def get_master_rating(self, master_id):
        rating_clean = 0.0
        rating_master = 0.0
        try:
            session = Session()
            row = session.query(Master, func.ifnull(func.avg(Rating.rate_clean), 0), func.ifnull(func.avg(Rating.rate_master), 0)) \
                            .outerjoin(Rating, Rating.master_id == Master.id) \
                            .filter(Master.id == master_id) \
                            .group_by(Master.id) \
                            .one()

            rating_clean    = row[1]
            rating_master   = row[2]

            rating_clean = float('%.2f' % rating_clean)
            rating_master = float('%.2f' % rating_master)

        except Exception, e:
            print 'master id :', master_id
            print_err_detail(e)

        finally:
            session.close()
            return rating_clean, rating_master


    def get_avg_master_cleaning_rating(self, master_id):
        rating_clean = 0.0
        rating_master = 0.0
        try:
            session = Session()
            row = session.query(Master, func.ifnull(func.avg(Rating.rate_clean), 0), func.ifnull(func.avg(Rating.rate_master), 0)) \
                            .outerjoin(Rating, Rating.master_id == Master.id) \
                            .filter(Master.id == master_id) \
                            .group_by(Master.id) \
                            .one()

            rating_clean    = row[1]
            rating_master   = row[2]

        except Exception, e:
            print 'master id :', master_id
            print_err_detail(e)

        finally:
            session.close()
            return (rating_clean + rating_master) / 2


    def get_master_total_granted_salary(self, master_id):
        total_salary = 0
        try:
            session = Session()
            row = session.query(Master, func.ifnull(func.sum(MasterSalary.amount), 0), MasterSalary.grant_date) \
                            .outerjoin(MasterSalary, MasterSalary.master_id == Master.id) \
                            .filter(Master.id == master_id) \
                            .group_by(Master.id) \
                            .one()

            total_salary = row[1]

        except Exception, e:
            print 'master id :', master_id
            print_err_detail(e)

        finally:
            session.close()
            return total_salary


    def get_master_last_month_granted_salary(self, master_id):
        last_month_salary = 0
        try:
            last_month = dt.date.today().month - 1

            session = Session()
            row = session.query(Master, func.ifnull(func.sum(MasterSalary.amount), 0), MasterSalary.grant_date) \
                            .outerjoin(MasterSalary, MasterSalary.master_id == Master.id) \
                            .filter(Master.id == master_id).filter(func.month(MasterSalary.grant_date) == last_month) \
                            .group_by(Master.id) \
                            .one()

            last_month_salary = row[1]

        except Exception, e:
            #print 'master id :', master_id, ' no salary last month'
            last_month_salary = 0

        finally:
            session.close()
            return last_month_salary

    def get_master_prefered_area(self, master_id):
        prefered_area = ''
        try:
            session = Session()
            row = session.query(Master, func.group_concat(MasterPreferedArea.prefered_gu), func.group_concat(Sigungu.name)) \
                            .outerjoin(MasterPreferedArea, MasterPreferedArea.master_id == Master.id) \
                            .outerjoin(Sigungu, MasterPreferedArea.prefered_gu == Sigungu.id) \
                            .filter(Master.id == master_id) \
                            .order_by(Sigungu.name) \
                            .group_by(Master.id) \
                            .one()

            prefered_area = row[2]

            if prefered_area == None:
                prefered_area = ''

        except Exception, e:
            print 'master id :', master_id
            print_err_detail(e)

        finally:
            session.close()
            return prefered_area

    def is_day_off(self, master_id, date):
        day_off = False
        print master_id, date, type(date)
        try:
            session = Session()
            row = session.query(MasterScheduleByDate) \
                        .filter(MasterScheduleByDate.master_id == master_id) \
                        .filter(MasterScheduleByDate.date == date) \
                        .one()


            if row.active == 0:
                day_off = True

        except Exception, e:
            #print_err_detail(e)
            pass
        finally:
            session.close()
            return day_off

    def get_master_working_time(self, master_id):
        master_start_times = ',,,,,,'
        master_end_times = ',,,,,,'

        try:
            session = Session()
            result = session.query(Master, MasterTimeSlot) \
                            .join(MasterTimeSlot, MasterTimeSlot.master_id == Master.id) \
                            .filter(Master.id == master_id) \
                            .order_by(MasterTimeSlot.day_of_week) \
                            .all()

            start_times = ['', '', '', '', '', '', '']
            end_times   = ['', '', '', '', '', '', '']

            for r in result:
                dow = int(r.MasterTimeSlot.day_of_week)
                start_times[dow] = str(r.MasterTimeSlot.start_time.hour)
                end_times[dow] = str(r.MasterTimeSlot.end_time.hour)

            master_start_times = ','.join(start_times)
            master_end_times = ','.join(end_times)

        except Exception, e:
            print 'master_id :', master_id
            print_err_detail(e)

        finally:
            session.close()
            return master_start_times, master_end_times

    def get_master_working_time_for_day(self, master_id, date):
        start_hour = 8
        end_hour = 8
        try:
            session = Session()
            row = session.query(MasterScheduleByDate) \
                        .filter(MasterScheduleByDate.master_id == master_id) \
                        .filter(MasterScheduleByDate.date == date) \
                        .one()

            start_hour = row.free_from.hour
            end_hour = row.free_to.hour

        except Exception, e:
            #print_err_detail(e)
            start_hour = 8
            end_hour = 8

        finally:
            session.close()
            return start_hour, end_hour

    def get_available_master_in_sigungu(self, sigungu_id):
        master_ids = []

        try:
            session = Session()
            result = session.query(MasterPreferedArea).filter(MasterPreferedArea.prefered_gu == sigungu_id).all()

            for row in result:
                master_ids.append(row.master_id)

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()
            return master_ids

    def get_available_time_by_date(self, master_id):
        available_times = {}

        try:
            session = Session()
            result = session.query(MasterTimeSlot) \
                        .filter(MasterTimeSlot.master_id == master_id) \
                        .order_by(MasterTimeSlot.day_of_week) \
                        .all()

            for row in result:
                available_times[row.day_of_week] = (row.start_time, row.end_time)

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()
            return available_times

    def get_master_schedule_max_date(self):
        value = dt.datetime.today()
        try:
            session = Session()
            value = session.query(func.max(MasterScheduleByDate.date)).scalar()

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()

            return value

    def get_master_name_img_and_average_rating(self, master_id):
        name = ''
        img_url = ''
        rating = 0

        try:
            session = Session()
            row = session.query(Master.name, func.ifnull(Master.img_url, ''), (func.ifnull(func.avg(Rating.rate_clean), 0) + func.ifnull(func.avg(Rating.rate_master), 0)) / 2 ) \
                    .outerjoin(Rating, Master.id == Rating.master_id) \
                    .filter(Master.id == master_id) \
                    .group_by(Master.id) \
                    .one()

            name = row[0]
            img_url = row[1]
            rating = row[2]

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()
            if rating <= 0:
                rating = 4.5
            return name, img_url, rating


    def get_average_master_rating(self):
        session = Session()
        result = session.query(func.avg((Rating.rate_clean + Rating.rate_master) / 2).label('avg_rating'), Booking.master_id) \
                    .outerjoin(Booking, Rating.booking_id == Booking.id) \
                    .group_by(Booking.master_id) \
                    .all()

        for row in result:
            print row

        session.close()

    def get_distinct_req_ids(self, master_id):
        req_ids = []
        try:
            session = Session()

            result = session.query(Booking.request_id).filter(Booking.master_id == master_id).distinct()

            for row in result:
                req_ids.append(row.request_id)

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()
            return req_ids

    def is_master_off_date(self, master_id, date):
        try:
            session = Session()
            row = session.query(MasterScheduleByDate) \
                    .filter(MasterScheduleByDate.master_id == master_id) \
                    .filter(MasterScheduleByDate.date == date) \
                    .one()

            print  master_id, date, row.active
            if row.active == 1:
                return False

            return True
        except Exception, e:
            print_err_detail(e)
            return True
        finally:
            session.close()

    def is_master_available_next_schedule(self, booking_id, changed_time_in_minutes):
        time = None
        try:
            session = Session()
            row = session.query(Booking).filter(Booking.id == booking_id).one()

            master_id   = row.master_id
            start_time  = row.start_time
            end_time    = row.estimated_end_time
            date        = start_time.date()

            org_taking_time = time_to_minutes(timedelta_to_time(end_time - start_time))
            new_taking_time = org_taking_time + changed_time_in_minutes

            new_estimated_end_time = start_time + dt.timedelta(minutes=new_taking_time)

            print new_estimated_end_time

            value = session.query(func.min(Booking.start_time)).filter(Booking.master_id == master_id) \
                                .filter(func.date(Booking.start_time) == date) \
                                .filter(Booking.start_time > start_time) \
                                .filter(Booking.cleaning_status == BC.BOOKING_UPCOMMING) \
                                .scalar()

            print value
            if value == None: # no schedule
                work_date = start_time.date()
                schedule_date = session.query(MasterScheduleByDate) \
                                        .filter(MasterScheduleByDate.master_id == master_id) \
                                        .filter(MasterScheduleByDate.date == work_date) \
                                        .one()

                free_to = schedule_date.free_to
                if free_to < new_estimated_end_time.time():
                    time = None
                else:
                    time = new_estimated_end_time
            else:
                if new_estimated_end_time + dt.timedelta(hours = 1) <= value:
                    time = new_estimated_end_time
                else:
                    time = None

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()
            return time


    def is_schedule_extend_available(self, booking_id, total_time):
        time = None
        try:
            session = Session()
            row = session.query(Booking).filter(Booking.id == booking_id).one()

            master_id   = row.master_id
            start_time  = row.start_time
            end_time    = row.estimated_end_time
            date        = start_time.date()

            new_estimated_end_time = start_time + dt.timedelta(minutes=total_time)

            next_start_time = session.query(func.min(Booking.start_time)).filter(Booking.master_id == master_id) \
                                .filter(func.date(Booking.start_time) == date) \
                                .filter(Booking.start_time > start_time) \
                                .filter(Booking.cleaning_status == BC.BOOKING_UPCOMMING) \
                                .scalar()

            if next_start_time == None: # no schedule
                schedule_date = session.query(MasterScheduleByDate) \
                                        .filter(MasterScheduleByDate.master_id == master_id) \
                                        .filter(MasterScheduleByDate.date == date) \
                                        .one()

                free_to = schedule_date.free_to
                if free_to < new_estimated_end_time.time():
                    time = None
                else:
                    time = new_estimated_end_time
            else:
                if new_estimated_end_time + dt.timedelta(minutes = 60) < next_start_time:
                    time = new_estimated_end_time
                else:
                    time = None

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()
            return time


    def get_master_bookings(self, master_id):
        bookings = []
        try:
            session = Session()
            userdao = UserDAO()
            result = session.query(Booking, UserAddress) \
                            .join(UserAddress, and_(Booking.user_id == UserAddress.user_id, Booking.addr_idx == UserAddress.user_addr_index)) \
                            .filter(Booking.master_id == master_id) \
                            .all()

            for row in result:

                key = userdao.get_user_salt_by_id(row.Booking.user_id)[:16]
                crypto = aes.MyCrypto(key)

                booking_info = {}
                booking_info['booking_id'] = row.Booking.id
                booking_info['appointment_type'] = row.Booking.appointment_type
                booking_info['start_time'] = row.Booking.start_time
                booking_info['estimated_end_time'] = row.Booking.estimated_end_time
                booking_info['address'] = crypto.decodeAES(row.UserAddress.address)
                booking_info['geohash5'] = row.UserAddress.geohash5
                booking_info['geohash6'] = row.UserAddress.geohash6

                bookings.append(booking_info)

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()
            return bookings

    def get_masterid_and_starttime_from_booking(self, booking_id):
        master_id = ''
        start_time = ''
        try:
            session = Session()
            row = session.query(Booking) \
                        .filter(Booking.id == booking_id) \
                        .one()

            master_id = row.master_id
            start_time = int(dt.datetime.strftime(row.start_time, '%Y%m%d'))

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()
            return master_id, start_time



    def get_recommended_schedule(self, gu_id, have_pet, master_gender, appointment_type, geohash6, now):
        result_list = []

        try:
            session = Session()
            sql = 'select  s.*, \
                    time(t.start_time) as start_time, \
                    time(t.estimated_end_time) as end_time, \
                    time(t4.start_time) as prev_start_time, \
                    time(t4.estimated_end_time) as prev_end_time,\
                    t4.geohash5 as prev_geo5, t4.geohash6 as prev_geo6,\
                    time(t3.start_time) as next_start_time, \
                    time(t3.estimated_end_time) as next_end_time,\
                    t3.geohash5 as next_geo5, t3.geohash6 as next_geo6,\
                    t.geohash5, t.geohash6,\
                    ifnull(t2.average_rate, 0) as average_rate,\
                    m.level\
                from master_schedules_by_date s \
                left join (select b.master_id, b.appointment_type, b.start_time, b.estimated_end_time, a.geohash5, a.geohash6 \
                            from bookings b \
                            left join user_addresses a \
                            on b.user_id = a.user_id and b.addr_idx = a.user_addr_index \
                            where b.cleaning_status = 0\
                          ) t \
                on t.master_id = s.master_id and s.date = date(t.start_time) \
                join master_prefered_area pa \
                on pa.master_id = s.master_id and pa.prefered_gu = :gu_id \
                left join (select master_id, (avg(rate_clean) + avg(rate_master)) / 2 as average_rate  \
                            from ratings \
                            group by master_id \
                          ) t2 \
                on s.master_id = t2.master_id \
                join masters m on m.id = s.master_id and m.active = 1'

            if have_pet == 1: #
                sql += ' and m.pet_alergy = 0'

            if master_gender == 1: # 여자를 원할 경우
                sql += ' and m.gender = 1'
            elif master_gender == 2: # 남자를 원할 경우
                sql += ' and m.gender = 0'

            sql += ' left join (select b2.master_id, b2.start_time, b2.estimated_end_time, b2.cleaning_status, a2.geohash5, a2.geohash6 from bookings b2 \
                                    join user_addresses a2 \
                                    on b2.user_id = a2.user_id \
                                    and b2.addr_idx = a2.user_addr_index \
                                    where b2.cleaning_status = 0) t3 \
                on s.date = date(t3.start_time) and s.master_id = t3.master_id and \
                t3.start_time = (select min(t3.start_time) \
                                                from bookings t3 \
                                                where s.master_id = t3.master_id \
                                                and s.date = date(t3.start_time) \
                                                and t.estimated_end_time < t3.start_time \
                                                and t3.cleaning_status = 0) \
                left join (select b3.master_id, b3.start_time, b3.estimated_end_time, b3.cleaning_status, a3.geohash5, a3.geohash6 from bookings b3 \
                                    join user_addresses a3 \
                                    on b3.user_id = a3.user_id \
                                    and b3.addr_idx = a3.user_addr_index \
                                    where b3.cleaning_status = 0) t4 \
                on s.date = date(t4.start_time) and s.master_id = t4.master_id and \
                t4.estimated_end_time = (select max(t4.estimated_end_time) \
                                                from bookings t4 \
                                                where s.master_id = t4.master_id \
                                                and s.date = date(t4.start_time) \
                                                and t.start_time > t4.estimated_end_time \
                                                and t4.cleaning_status = 0)'

            sql += 'where t.appointment_type = :appointment_type and t.geohash6 = :geohash6 and s.date > :now'
            query_param = {'gu_id' : gu_id, 'appointment_type' : appointment_type, 'geohash6' : geohash6, 'now' : now}


            sql += ' order by t2.average_rate desc, m.dateofreg , s.date, start_time'
            result = session.execute(sql, query_param).fetchall()

            for row in result:
                result_list.append(dict(row))

        except Exception, e:
            session.rollback()
            print_err_detail(e)

        finally:
            session.close()
            return result_list



    def get_master_schedule_by_dates(self, gu_id, have_pet, master_gender, date_list, master_id = None):
        result_list = []

        try:
            session = Session()
            sql = 'select  s.*, \
                    time(t.start_time) as start_time, \
                    time(t.estimated_end_time) as end_time, \
                    time(t4.start_time) as prev_start_time, \
                    time(t4.estimated_end_time) as prev_end_time,\
                    t4.geohash5 as prev_geo5, t4.geohash6 as prev_geo6,\
                    time(t3.start_time) as next_start_time, \
                    time(t3.estimated_end_time) as next_end_time,\
                    t3.geohash5 as next_geo5, t3.geohash6 as next_geo6,\
                    t.address, t.geohash5, t.geohash6,\
                    ifnull(t2.average_rate, 0) as average_rate,\
                    m.level\
                from master_schedules_by_date s \
                left join (select b.master_id, b.start_time, b.estimated_end_time, a.address, a.geohash5, a.geohash6 \
                            from bookings b \
                            left join user_addresses a \
                            on b.user_id = a.user_id and b.addr_idx = a.user_addr_index \
                            where b.cleaning_status = 0\
                          ) t \
                on t.master_id = s.master_id and s.date = date(t.start_time) \
                join master_prefered_area pa \
                on pa.master_id = s.master_id and pa.prefered_gu = :gu_id \
                left join (select master_id, (avg(rate_clean) + avg(rate_master)) / 2 as average_rate  \
                            from ratings \
                            group by master_id \
                          ) t2 \
                on s.master_id = t2.master_id \
                join masters m on m.id = s.master_id and m.active = 1'

            if have_pet == 1: #
                sql += ' and m.pet_alergy = 0'

            if master_gender == 1: # 여자를 원할 경우
                sql += ' and m.gender = 1'
            elif master_gender == 2: # 남자를 원할 경우
                sql += ' and m.gender = 0'

            sql += ' left join (select b2.master_id, b2.start_time, b2.estimated_end_time, b2.cleaning_status, a2.address, a2.geohash5, a2.geohash6 from bookings b2 \
                                    join user_addresses a2 \
                                    on b2.user_id = a2.user_id \
                                    and b2.addr_idx = a2.user_addr_index \
                                    where b2.cleaning_status = 0) t3 \
                on s.date = date(t3.start_time) and s.master_id = t3.master_id and \
                t3.start_time = (select min(t3.start_time) \
                                                from bookings t3 \
                                                where s.master_id = t3.master_id \
                                                and s.date = date(t3.start_time) \
                                                and t.estimated_end_time < t3.start_time \
                                                and t3.cleaning_status = 0) \
                left join (select b3.master_id, b3.start_time, b3.estimated_end_time, b3.cleaning_status, a3.address, a3.geohash5, a3.geohash6 from bookings b3 \
                                    join user_addresses a3 \
                                    on b3.user_id = a3.user_id \
                                    and b3.addr_idx = a3.user_addr_index \
                                    where b3.cleaning_status = 0) t4 \
                on s.date = date(t4.start_time) and s.master_id = t4.master_id and \
                t4.estimated_end_time = (select max(t4.estimated_end_time) \
                                                from bookings t4 \
                                                where s.master_id = t4.master_id \
                                                and s.date = date(t4.start_time) \
                                                and t.start_time > t4.estimated_end_time \
                                                and t4.cleaning_status = 0)'

            appointment_type = len(date_list)

            if appointment_type == 1: # 1회, 혹은 한번 해볼께요
                sql += 'where (s.date = :date1)'
                query_param = {'gu_id' : gu_id, 'date1' : date_list[0]}
            elif appointment_type == 4: # 정기
                sql += 'where (s.date = :date1 or s.date = :date2 or s.date = :date3 or s.date = :date4)'
                query_param = {'gu_id' : gu_id, 'date1' : date_list[0], 'date2' : date_list[1], 'date3' : date_list[2], 'date4' : date_list[3]}


            if master_id != None:
                sql += ' and s.master_id = :master_id'
                query_param['master_id'] = master_id


            sql += ' order by t2.average_rate desc, m.dateofreg , s.date, start_time'
            result = session.execute(sql, query_param).fetchall()

            for row in result:
                result_list.append(dict(row))

        except Exception, e:
            session.rollback()
            print_err_detail(e)

        finally:
            session.close()
            return result_list


    def find_master_by_score2(self, schedule_by_date_list, uid, gu_id, appointment_type, taking_minutes):
        try:
            available_dates_by_master = []

            prev_master_id = None

            for row in schedule_by_date_list:
                mid             = row['master_id']
                targetdate      = dt.datetime.strftime(row['date'], '%Y%m%d')

                free_from       = timedelta_to_time(row['free_from'])
                free_to         = timedelta_to_time(row['free_to'])
                start_time      = timedelta_to_time(row['start_time'])
                end_time        = timedelta_to_time(row['end_time'])
                prev_start_time = timedelta_to_time(row['prev_start_time'])
                prev_end_time   = timedelta_to_time(row['prev_end_time'])
                next_start_time = timedelta_to_time(row['next_start_time'])
                next_end_time   = timedelta_to_time(row['next_end_time'])

                avg_rate        = row['average_rate']

                schedule = {}

                schedule['mid']         = mid
                schedule['date']        = targetdate
                schedule['take_time']   = taking_minutes

                if start_time == None: # 일이 할당되지 않아 명시한 시간만큼 가능
                    schedule['move_in']         = 0
                    schedule['move_out']        = 0
                    schedule['available_from']  = time_added_minute(free_from, schedule['move_in'])
                    schedule['available_to']    = time_substracted_minute(free_to, schedule['move_out'])
                    schedule['score']           = self.make_score(new_geohash6, [geohash5], [geohash6], avg_rate, level)

                    schedule['prev_end_time'] = None
                    schedule['next_start_time'] = None

                    if schedule['available_from'] < schedule['available_to']:
                        available_dates_by_master.append(schedule)
                else:
                    if prev_start_time != None and next_start_time != None: # 앞뒤 스케쥴이 있는 경우
                        schedule['move_in']         = get_moving_time(new_geohash6, prev_geohash6)
                        schedule['move_out']        = get_moving_time(new_geohash6, geohash6)

                        schedule['available_from']  = time_added_minute(prev_end_time, schedule['move_in'])
                        schedule['available_to']    = time_substracted_minute(start_time, schedule['move_out'])
                        schedule['prev_end_time']   = prev_end_time
                        schedule['next_start_time'] = start_time

                        if schedule['available_from'] < schedule['available_to']:
                            available_dates_by_master.append(schedule)

                        #####################################################################
                        schedule = schedule.copy()

                        schedule['move_in']         = get_moving_time(new_geohash6, geohash6) #30 if new_geohash6 == geohash6 else 60
                        schedule['move_out']        = get_moving_time(new_geohash6, next_geohash6) #30 if new_geohash6 == next_geohash6 else 60
                        schedule['available_from']  = time_added_minute(end_time, schedule['move_in'])
                        schedule['available_to']    = time_substracted_minute(next_start_time, schedule['move_out'])
                        schedule['score']           = self.make_score(new_geohash6, [geohash5, next_geohash5], [geohash6, next_geohash6], avg_rate, level)

                        schedule['prev_end_time'] = end_time
                        schedule['next_start_time'] = next_start_time

                        if schedule['available_from'] < schedule['available_to']:
                            available_dates_by_master.append(schedule)

                    elif prev_start_time != None: # 앞 스케쥴만 있는 경우
                        schedule['move_in']         = get_moving_time(new_geohash6, geohash6) #30 if new_geohash6 == geohash6 else 60
                        schedule['move_out']        = 0
                        schedule['available_from']  = time_added_minute(end_time, schedule['move_in'])
                        schedule['available_to']    = time_substracted_minute(free_to, schedule['move_out'])
                        schedule['score']           = self.make_score(new_geohash6, [geohash5], [geohash6], avg_rate, level)

                        schedule['prev_end_time'] = end_time
                        schedule['next_start_time'] = None

                        if schedule['available_from'] < schedule['available_to']:
                            available_dates_by_master.append(schedule)

                        schedule = schedule.copy() # 이곳은 뒤 스케쥴만 있는 경우와 중복이 될 수 있어서 여기서 한번만 처리한다.

                        schedule['move_in']         = get_moving_time(new_geohash6, prev_geohash6) #30 if new_geohash6 == geohash6 else 60
                        schedule['move_out']        = get_moving_time(new_geohash6, geohash6) #30 if new_geohash6 == geohash6 else 60
                        schedule['available_from']  = time_added_minute(prev_end_time, schedule['move_in'])
                        schedule['available_to']    = time_substracted_minute(start_time, schedule['move_out'])
                        schedule['score']           = self.make_score(new_geohash6, [geohash5], [geohash6], avg_rate, level)

                        schedule['prev_end_time'] = prev_end_time
                        schedule['next_start_time'] = start_time

                        if schedule['available_from'] < schedule['available_to']:
                            available_dates_by_master.append(schedule)

                    elif next_start_time != None: # 뒤 스케쥴만 있는 경우

                        schedule['move_in']         = 0
                        schedule['move_out']        = get_moving_time(new_geohash6, geohash6) #30 if new_geohash6 == geohash6 else 60
                        schedule['available_from']  = time_added_minute(free_from, schedule['move_in'])
                        schedule['available_to']    = time_substracted_minute(start_time, schedule['move_out'])
                        schedule['score']           = self.make_score(new_geohash6, [geohash5], [geohash6], avg_rate, level)

                        schedule['prev_end_time'] = None
                        schedule['next_start_time'] = start_time

                        if schedule['available_from'] < schedule['available_to']:
                            available_dates_by_master.append(schedule)

                    else: # 앞뒤 스케쥴이 없는 경우
                        schedule['move_in']         = 0
                        schedule['move_out']        = get_moving_time(new_geohash6, geohash6) #30 if new_geohash6 == geohash6 else 60
                        schedule['available_from']  = time_added_minute(free_from, schedule['move_in'])
                        schedule['available_to']    = time_substracted_minute(start_time, schedule['move_out'])
                        schedule['score']           = self.make_score(new_geohash6, [geohash5], [geohash6], avg_rate, level)

                        schedule['prev_end_time'] = None
                        schedule['next_start_time'] = start_time

                        if schedule['available_from'] < schedule['available_to']:
                            available_dates_by_master.append(schedule)

                        #####################################################################
                        schedule = schedule.copy()

                        schedule['move_in']         = get_moving_time(new_geohash6, geohash6) #30 if new_geohash6 == geohash6 else 60
                        schedule['move_out']        = 0
                        schedule['available_from']  = time_added_minute(end_time, schedule['move_in'])
                        schedule['available_to']    = time_substracted_minute(free_to, schedule['move_out'])
                        schedule['score']           = self.make_score(new_geohash6, [geohash5], [geohash6], avg_rate, level)

                        schedule['prev_end_time'] = end_time
                        schedule['next_start_time'] = None

                        if schedule['available_from'] < schedule['available_to']:
                            available_dates_by_master.append(schedule)

        except Exception, e:
            print_err_detail(e)




    def find_master_by_score(self, schedule_by_date_list, gu_id, uid, appointment_type, date_list,
                            time_range_begin, time_range_begin_min, time_range_end, time_range_end_min,
                            taking_minutes, new_geohash6, for_recommend = None):
        try:
            available_dates_by_master = []

            prev_master_id = None

            for row in schedule_by_date_list:
                mid             = row['master_id']
                targetdate      = dt.datetime.strftime(row['date'], '%Y%m%d')

                free_from       = timedelta_to_time(row['free_from'])
                free_to         = timedelta_to_time(row['free_to'])
                start_time      = timedelta_to_time(row['start_time'])
                end_time        = timedelta_to_time(row['end_time'])
                prev_start_time = timedelta_to_time(row['prev_start_time'])
                prev_end_time   = timedelta_to_time(row['prev_end_time'])
                next_start_time = timedelta_to_time(row['next_start_time'])
                next_end_time   = timedelta_to_time(row['next_end_time'])

                prev_geohash5   = row['prev_geo5']
                prev_geohash6   = row['prev_geo6']
                next_geohash5   = row['next_geo5']
                next_geohash6   = row['next_geo6']

                geohash5        = row['geohash5']
                geohash6        = row['geohash6']
                avg_rate        = row['average_rate']
                level           = row['level']

                schedule = {}

                schedule['mid'] = mid
                schedule['date'] = targetdate
                schedule['take_time']       = taking_minutes

                if start_time == None: # 일이 할당되지 않아 명시한 시간만큼 가능
                    schedule['move_in']         = 0
                    schedule['move_out']        = 0
                    schedule['available_from']  = time_added_minute(free_from, schedule['move_in'])
                    schedule['available_to']    = time_substracted_minute(free_to, schedule['move_out'])
                    schedule['score']           = self.make_score(new_geohash6, [geohash5], [geohash6], avg_rate, level)

                    schedule['prev_end_time'] = None
                    schedule['next_start_time'] = None

                    print mid, targetdate, schedule['available_from'], schedule['available_to'], '1'
                    if schedule['available_from'] < schedule['available_to']:
                        available_dates_by_master.append(schedule)
                else:
                    if prev_start_time != None and next_start_time != None: # 앞뒤 스케쥴이 있는 경우
                        print prev_start_time, next_start_time

                        schedule['move_in']         = get_moving_time(new_geohash6, prev_geohash6) #30 if new_geohash6 == prev_geohash6 else 60
                        schedule['move_out']        = get_moving_time(new_geohash6, geohash6)#30 if new_geohash6 == geohash6 else 60
                        schedule['available_from']  = time_added_minute(prev_end_time, schedule['move_in'])
                        schedule['available_to']    = time_substracted_minute(start_time, schedule['move_out'])
                        schedule['score']           = self.make_score(new_geohash6, [prev_geohash5, geohash5], [prev_geohash6, geohash6], avg_rate, level)

                        schedule['prev_end_time'] = prev_end_time
                        schedule['next_start_time'] = start_time

                        print mid, targetdate, schedule['available_from'], schedule['available_to'], '2'
                        if schedule['available_from'] < schedule['available_to']:
                            available_dates_by_master.append(schedule)

                        #####################################################################
                        schedule = schedule.copy()

                        schedule['move_in']         = get_moving_time(new_geohash6, geohash6) #30 if new_geohash6 == geohash6 else 60
                        schedule['move_out']        = get_moving_time(new_geohash6, next_geohash6) #30 if new_geohash6 == next_geohash6 else 60
                        schedule['available_from']  = time_added_minute(end_time, schedule['move_in'])
                        schedule['available_to']    = time_substracted_minute(next_start_time, schedule['move_out'])
                        schedule['score']           = self.make_score(new_geohash6, [geohash5, next_geohash5], [geohash6, next_geohash6], avg_rate, level)

                        schedule['prev_end_time'] = end_time
                        schedule['next_start_time'] = next_start_time

                        print mid, targetdate, schedule['available_from'], schedule['available_to'], '3'
                        if schedule['available_from'] < schedule['available_to']:
                            available_dates_by_master.append(schedule)

                    elif prev_start_time != None: # 앞 스케쥴만 있는 경우
                        schedule['move_in']         = get_moving_time(new_geohash6, geohash6) #30 if new_geohash6 == geohash6 else 60
                        schedule['move_out']        = 0
                        schedule['available_from']  = time_added_minute(end_time, schedule['move_in'])
                        schedule['available_to']    = time_substracted_minute(free_to, schedule['move_out'])
                        schedule['score']           = self.make_score(new_geohash6, [geohash5], [geohash6], avg_rate, level)

                        schedule['prev_end_time'] = end_time
                        schedule['next_start_time'] = None

                        print mid, targetdate, schedule['available_from'], schedule['available_to'], schedule['move_in'], schedule['prev_end_time'], '4'
                        if schedule['available_from'] < schedule['available_to']:
                            available_dates_by_master.append(schedule)

                        schedule = schedule.copy() # 이곳은 뒤 스케쥴만 있는 경우와 중복이 될 수 있어서 여기서 한번만 처리한다.

                        schedule['move_in']         = get_moving_time(new_geohash6, prev_geohash6) #30 if new_geohash6 == geohash6 else 60
                        schedule['move_out']        = get_moving_time(new_geohash6, geohash6) #30 if new_geohash6 == geohash6 else 60
                        schedule['available_from']  = time_added_minute(prev_end_time, schedule['move_in'])
                        schedule['available_to']    = time_substracted_minute(start_time, schedule['move_out'])
                        schedule['score']           = self.make_score(new_geohash6, [geohash5], [geohash6], avg_rate, level)

                        schedule['prev_end_time'] = prev_end_time
                        schedule['next_start_time'] = start_time

                        print mid, targetdate, schedule['available_from'], schedule['available_to'], '5'
                        if schedule['available_from'] < schedule['available_to']:
                            available_dates_by_master.append(schedule)

                    elif next_start_time != None: # 뒤 스케쥴만 있는 경우

                        schedule['move_in']         = 0
                        schedule['move_out']        = get_moving_time(new_geohash6, geohash6) #30 if new_geohash6 == geohash6 else 60
                        schedule['available_from']  = time_added_minute(free_from, schedule['move_in'])
                        schedule['available_to']    = time_substracted_minute(start_time, schedule['move_out'])
                        schedule['score']           = self.make_score(new_geohash6, [geohash5], [geohash6], avg_rate, level)

                        schedule['prev_end_time'] = None
                        schedule['next_start_time'] = start_time

                        print mid, targetdate, schedule['available_from'], schedule['available_to'], '6'
                        if schedule['available_from'] < schedule['available_to']:
                            available_dates_by_master.append(schedule)

                    else: # 앞뒤 스케쥴이 없는 경우
                        schedule['move_in']         = 0
                        schedule['move_out']        = get_moving_time(new_geohash6, geohash6) #30 if new_geohash6 == geohash6 else 60
                        schedule['available_from']  = time_added_minute(free_from, schedule['move_in'])
                        schedule['available_to']    = time_substracted_minute(start_time, schedule['move_out'])
                        schedule['score']           = self.make_score(new_geohash6, [geohash5], [geohash6], avg_rate, level)

                        schedule['prev_end_time'] = None
                        schedule['next_start_time'] = start_time

                        print mid, targetdate, schedule['available_from'], schedule['available_to'], '7'
                        if schedule['available_from'] < schedule['available_to']:
                            available_dates_by_master.append(schedule)

                        #####################################################################
                        schedule = schedule.copy()

                        schedule['move_in']         = get_moving_time(new_geohash6, geohash6) #30 if new_geohash6 == geohash6 else 60
                        schedule['move_out']        = 0
                        schedule['available_from']  = time_added_minute(end_time, schedule['move_in'])
                        schedule['available_to']    = time_substracted_minute(free_to, schedule['move_out'])
                        schedule['score']           = self.make_score(new_geohash6, [geohash5], [geohash6], avg_rate, level)

                        schedule['prev_end_time'] = end_time
                        schedule['next_start_time'] = None


                        print mid, targetdate, schedule['available_from'], schedule['available_to'], '8'
                        if schedule['available_from'] < schedule['available_to']:
                            available_dates_by_master.append(schedule)


            print ''

            print 'before filtering...'
            for row in available_dates_by_master:
                print row

            print ''

            # sort by score and master_id
            #available_dates_by_master = sorted(available_dates_by_master, key = lambda x: (x['score'], x['mid']), reverse = True)
            available_dates_by_master = sorted(available_dates_by_master, key = lambda x: x['mid'], reverse = True)

            # filter1 -> filtering by taking time
            filtered_schedules = filter(lambda x : time_to_minutes(timedelta_to_time( dt.datetime.combine(dt.date.today(), x['available_to']) - dt.datetime.combine(dt.date.today(), x['available_from']))) >= x['take_time'], available_dates_by_master)


            filtered_group = groupby(filtered_schedules, lambda x: x['mid'])
            for k, fg in filtered_group:
                group_items = list(fg)
                max_available_from = max(group_items, key = lambda x:x['available_from'])['available_from']
                max_available_to = min(filter(lambda x:x['available_to'] > max_available_from, group_items), key = lambda x:x['available_to'])['available_to']

                min_available_to   = min(group_items, key = lambda x:x['available_to'])['available_to']
                min_available_from = max(filter(lambda x:x['available_from'] < min_available_to, group_items), key = lambda x:x['available_from'])['available_from']

                score = sum([x['score'] for x in group_items])

                for element in group_items:
                    element['max_available_from']   = max_available_from
                    element['max_available_to']     = max_available_to

                    element['min_available_from']   = min_available_from
                    element['min_available_to']     = min_available_to
                    element['score'] = score


            filtered_schedules_copy = copy.deepcopy(filtered_schedules)

            for item in filtered_schedules:
                item['min_available_to'] = item['max_available_to']
                del item['max_available_to']
                del item['min_available_from']

            for item in filtered_schedules_copy:
                item['max_available_from'] = item['min_available_from']
                del item['max_available_to']
                del item['min_available_from']

            filtered_schedules.extend(filtered_schedules_copy)

            print ''
            print 'max and min filtering...'
            for row in filtered_schedules:
                print row

            # filter2 -> filter by time range
            time_range_filter = self.make_time_range_filter(time_range_begin, time_range_begin_min, time_range_end, time_range_end_min, taking_minutes)
            filtered_schedules = filter(time_range_filter, filtered_schedules)

            # remove duplicate
            filtered_schedules = list(np.unique(np.array(filtered_schedules)))

            # sort by score and master_id
            filtered_schedules = sorted(filtered_schedules, key = lambda x: (x['score'], x['mid'], x['start_time']), reverse = True)

            print ''
            print 'after filtering...'
            for row in filtered_schedules:
                print row

            holder = IntermediateValueHolder()

            # 1회 예약의 경우
            if appointment_type == BC.ONE_TIME_BUT_CONSIDERING or appointment_type == BC.ONE_TIME:
                for schedule in filtered_schedules:
                    if for_recommend:
                        search_key = '%s_%s' % (schedule['mid'], schedule['date'])
                    else:
                        search_key = '%s_%d' % (schedule['mid'], date_list[0])
                    store_key = '%s_%s_%d' % (uid, search_key, appointment_type)

                    candidate = schedule
                    # check if the time is stored in memory
                    if holder.store(search_key, 1):
                        holder.store(store_key, [candidate])
                        return 'SUCCESS', '', store_key, [search_key], [candidate]

                self.add_master_deficiency(gu_id, uid)
                return 'NOTFOUND', 'NO HOMEMASTER AVAILABLE', None, [], []

            #정기 예약의 경우
            else:
                groupped_by_master = groupby(filtered_schedules, lambda x:(x['mid'], x['start_time'], x['end_time']))

                for key, group in groupped_by_master:
                    items = list(group)

                    print key, len(items)

                    temp_date_arr = []
                    for it in items:
                        print it['date']
                        temp_date_arr.append(int(it['date']))
                    print '%' * 80

                    if len(items) == 4:
                        if for_recommend:
                            search_keys = ['%s_%s' % (it['mid'], it['date']) for it in items]
                        else:
                            if set(temp_date_arr) == set(date_list):
                                search_keys = ['%s_%d' % (items[0]['mid'], d) for d in date_list]
                        store_key = '%s_%s_%d' % (uid, search_keys[0], appointment_type)

                        # check if the times are stored in memory
                        if holder.store_all(search_keys, 1):
                            holder.store(store_key, items)
                            return 'SUCCESS', '', store_key, search_keys, items

                self.add_master_deficiency(gu_id, uid)
                return 'NOTFOUND', 'NO HOMEMASTER AVAILABLE', None, [], []
        except Exception, e:
            print_err_detail(e)

            return 'ERROR', str(e), None, [], []


    def add_master_deficiency(self, gu_id, user_id):
        try:
            session = Session()

            md = MasterDeficiency(gu_id = gu_id, user_id = user_id)
            session.add(md)
            session.commit()
        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()


    def make_score(self, new_geohash6, geohash5s, geohash6s, avg_rate, level):
        score = 0

        if geohash6s != [None] and geohash5s != [None]:
            for i in xrange(len(geohash5s)):
                g5 = geohash5s[i]
                g6 = geohash6s[i]

                if new_geohash6 == g6:
                    score += 30
                elif new_geohash6 in geohash.neighbors(g6):
                    score += 10
                elif new_geohash6[:-1] == g5:
                    score += 3

        score += avg_rate
        score += level

        return score


    def make_time_range_filter(self, begin, begin_min, end, end_min, taking_minutes):
        def tr_filter(x):
            time_begin = dt.time(begin, begin_min)
            time_end = dt.time(end, end_min)

            if time_end < x['max_available_from'] or time_begin > x['min_available_to']:
                return False

            if x['next_start_time'] != None and x['next_start_time'] < time_end:
                time_end = x['min_available_to']

            if x['prev_end_time'] != None and x['prev_end_time'] > time_begin:
                time_begin = x['max_available_from']


            #if ((x['prev_end_time'] == None and x['next_start_time'] == None) or (x['prev_end_time'] != None and x['next_start_time'] != None)):
            if x['max_available_from'] > time_begin:
                time_begin = x['max_available_from']

            if x['min_available_to'] < time_end:
                time_end = x['min_available_to']


            '''if x['prev_end_time'] == None and x['next_start_time'] != None: # 스케쥴이 앞에 없다면 뒤에서 부터 확인함
                cur_time = time_end
                while cur_time >= time_begin: # 고객이 원하는 시간 범위, 앞에서 부터 되는지 확인함.
                    if x['available_from'] <= cur_time < x['available_to'] \
                        and x['available_from'] < time_added_minute(cur_time, taking_minutes) <= x['available_to'] :
                        x['start_time'] = cur_time
                        x['end_time']   = time_added_minute(cur_time, taking_minutes)

                        return True

                    cur_time = time_added_minute(cur_time, -30)
            #elif x['prev_end_time'] != None and x['next_start_time'] == None
            else:'''
            cur_time = time_begin

            while cur_time <= time_end: # 고객이 원하는 시간 범위, 앞에서 부터 되는지 확인함.
                if x['available_from'] <= cur_time < x['available_to'] \
                    and x['available_from'] < time_added_minute(cur_time, taking_minutes) <= x['available_to'] :
                    x['start_time'] = cur_time
                    x['end_time']   = time_added_minute(cur_time, taking_minutes)

                    return True

                cur_time = time_added_minute(cur_time, 30)

        return tr_filter


if __name__ == '__main__':
    masterdao = MasterDAO()
    print masterdao.is_valid_master('053b91ea-f9de-40d8-b872-296cac3251ee')
    print masterdao.is_valid_master('02a0d869-c8ef-4655-ba9e-741f5ade800f')
    print masterdao.is_valid_master('0dd3b91ea-f9de-40d8-b872-296cac3251ee')

    #master_id = 'd0060b43-d1e4-4b48-aa53-b6817913275d'
    #print masterdao.get_master_penalties(master_id, dt.datetime(2016, 5, 14), dt.datetime(2016, 5, 20))
    #print masterdao.get_master_penalties(master_id, dt.datetime(2016, 5, 21), dt.datetime(2016, 5, 27))
    #print masterdao.get_master_penalties(master_id, dt.datetime(2016, 5, 28), dt.datetime(2016, 6, 3))
    #print masterdao.get_master_penalties(master_id, dt.datetime(2016, 6, 4), dt.datetime(2016, 6, 10))
