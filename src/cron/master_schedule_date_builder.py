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
from data.session.mysql_session import engine, Session
from data.model.data_model import MasterScheduleByDate
from data.dao.masterdao import MasterDAO
from err.error_handler import print_err_detail, err_dict

# 최초 한번 빌드 하는 기능
# 홈마스터가 새로 들어오면 최대 날짜까지 빌드하는 기능
# 홈마스터가 나가면 해당 홈마스터 데이터 모두 삭제
# 일주일별로 그 다음 한주를 더 하는 기능
class ScheduleBuilder(object):
    def __init__(self):
        pass

    def initial_build_schedule(self):
        try:
            # 모든 홈마스터에 대해, 오늘 이후 20주 데이터 빌드 (140 days)
            NUM_DAYS = 140

            session = Session()

            masterdao = MasterDAO()
            master_ids = masterdao.get_all_master_ids()

            for mid in master_ids:
                today = dt.datetime.now()

                free_times_by_date = masterdao.get_available_time_by_date(mid)

                for i in xrange(NUM_DAYS):
                    date = today + dt.timedelta(days=(i+1))
                    free_times = free_times_by_date[date.weekday()] if date.weekday() in free_times_by_date else None

                    if free_times != None:
                        free_from = free_times[0]
                        free_to   = free_times[1]

                        schedule_by_date = MasterScheduleByDate(master_id = mid, date = date.date(), free_from = free_from, free_to = free_to)
                        session.add(schedule_by_date)

            session.commit()

        except Exception, e:
            session.rollback()
            print_err_detail(e)

        finally:
            session.close()

        return True

    # test 완료
    def build_schedule_weekly(self):
        try:
            DAYS_IN_A_WEEK = 7

            session = Session()

            masterdao = MasterDAO()
            max_date = masterdao.get_master_schedule_max_date()
            master_ids = masterdao.get_all_master_ids()

            for mid in master_ids:
                free_times_by_date = masterdao.get_available_time_by_date(mid)

                for i in xrange(DAYS_IN_A_WEEK):
                    date = max_date + dt.timedelta(days=i+1)
                    free_times = free_times_by_date[date.weekday()] if date.weekday() in free_times_by_date else None

                    if free_times != None:
                        free_from = free_times[0]
                        free_to   = free_times[1]

                        schedule_by_date = MasterScheduleByDate(master_id = mid, date = date, free_from = free_from, free_to = free_to)
                        session.add(schedule_by_date)

            session.commit()
            print 'build schedule weekly successfully performed its task in', dt.datetime.now()

        except Exception, e:
            session.rollback()
            print_err_detail(e)

        finally:
            session.close()

    def add_new_master_schedule(self, master_id):
        try:
            session = Session()

            masterdao = MasterDAO()
            max_date = masterdao.get_master_schedule_max_date()
            free_times_by_date = masterdao.get_available_time_by_date(master_id)

            print free_times_by_date

            current_date = dt.datetime.now().date() + dt.timedelta(days=1)

            print current_date, max_date

            while current_date <= max_date:
                free_times = free_times_by_date[current_date.weekday()] if current_date.weekday() in free_times_by_date else None

                if free_times != None:
                    free_from = free_times[0]
                    free_to   = free_times[1]

                    schedule_by_date = MasterScheduleByDate(master_id = master_id, date = current_date, free_from = free_from, free_to = free_to)
                    session.add(schedule_by_date)

                current_date += dt.timedelta(days=1)

            session.commit()
            print 'build schedule successfully performed its task for master', master_id, 'in', dt.datetime.now()


        except Exception, e:
            session.rollback()
            print_err_detail(e)

        finally:
            session.close()


    def update_new_master_schedule_with_active(self, master_id, non_active_dates):
        try:
            session = Session()

            masterdao = MasterDAO()
            max_date = masterdao.get_master_schedule_max_date()
            free_times_by_date = masterdao.get_available_time_by_date(master_id)

            print free_times_by_date

            current_date = dt.datetime.now().date() + dt.timedelta(days=1)

            print current_date, max_date

            while current_date <= max_date:
                free_times = free_times_by_date[current_date.weekday()] if current_date.weekday() in free_times_by_date else None

                if free_times != None:
                    free_from = free_times[0]
                    free_to   = free_times[1]

                    active = 1
                    if current_date in non_active_dates:
                        active = 0

                    schedule_by_date = MasterScheduleByDate(master_id = master_id, date = current_date, free_from = free_from, free_to = free_to, active = active)
                    session.add(schedule_by_date)

                current_date += dt.timedelta(days=1)

            session.commit()
            print 'build schedule successfully performed its task for master', master_id, 'in', dt.datetime.now()


        except Exception, e:
            session.rollback()
            print_err_detail(e)

        finally:
            session.close()


    def add_new_master_schedule_from_start_date(self, master_id, start_date):
        try:
            session = Session()

            masterdao = MasterDAO()
            max_date = masterdao.get_master_schedule_max_date()
            free_times_by_date = masterdao.get_available_time_by_date(master_id)

            print free_times_by_date

            current_date = start_date.date()

            print current_date, max_date

            while current_date <= max_date:
                free_times = free_times_by_date[current_date.weekday()] if current_date.weekday() in free_times_by_date else None

                if free_times != None:
                    free_from = free_times[0]
                    free_to   = free_times[1]

                    schedule_by_date = MasterScheduleByDate(master_id = master_id, date = current_date, free_from = free_from, free_to = free_to)
                    session.add(schedule_by_date)

                current_date += dt.timedelta(days=1)

            session.commit()
            print 'build schedule successfully performed its task for master', master_id, 'in', dt.datetime.now()


        except Exception, e:
            session.rollback()
            print_err_detail(e)

        finally:
            session.close()


    def delete_all_schedule_of_master(self, master_id):
        pass




if __name__ == '__main__':
    schedule_builder = ScheduleBuilder()
    schedule_builder.build_schedule_weekly()
    #schedule_builder.initial_build_schedule()
