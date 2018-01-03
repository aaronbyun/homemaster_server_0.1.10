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
import requests
import operator
import collections
import numpy as np
import functools as func
import pickle
import datetime as dt
import rest.booking.booking_constant as BC
from nptime import nptime
from utils.datetime_utils import time_to_str, timedelta_to_time, time_to_minutes
from utils.geo_utils import get_moving_time
from data.session.mysql_session import engine, Session
from data.intermediate.value_holder import IntermediateValueHolder
from data.model.data_model import UserPaymentRecord, Booking, UserDefaultAddress, UserDefaultCard
from data.dao.userdao import UserDAO
from data.dao.addressdao import AddressDAO
from data.dao.masterdao import MasterDAO
from err.error_handler import print_err_detail, err_dict
from rest.response import Response, add_err_message_to_response, add_err_ko_message_to_response
from data.intermediate.value_holder import IntermediateValueHolder
from sqlalchemy.exc import IntegrityError
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel


class HMScheduler():
    DAYS_OF_WEEK = 7

    def get_occupied_slots(self, gu_id, appointment_type, by_manager, start_date, end_date, prefer_women,
                            have_pet, master_id = '', request_id = ''):
        print 'request_id', request_id
        query_param = {'gu_id' : gu_id, 'start_date' : start_date, 'end_date' : end_date}

        sql = '''select  s.master_id, m.name, s.date, s.free_from, s.free_to,
                time(t.start_time) as start_time,
                time(t.estimated_end_time) as end_time,
                t.geohash6, t.latitude as lat, t.longitude as lng
                from master_schedules_by_date s
                join masters m
                on m.id = s.master_id and m.active = 1'''

        if appointment_type in [BC.ONE_TIME_A_MONTH, BC.TWO_TIME_A_MONTH, BC.FOUR_TIME_A_MONTH] and by_manager == 0:
            sql += ''' join (select master_id, count(*) as cnt
							from bookings
                            where cleaning_status = 2
                            group by master_id
                            having count(*) > 5
                            and master_id not in (select master_id from master_only_onetime)) tt
                on m.id  = tt.master_id'''

        if have_pet == True: # 애완동물이 있는 경우, 엘러지가 없는 홈마스터 핉터링
            sql += ' and m.pet_alergy = 0'

        if prefer_women == True: # 여자 홈마스터를 원할 경우
            sql += ' and m.gender = 1'

        sql += ''' left join (select b.master_id, b.start_time, b.estimated_end_time, a.geohash6, a.latitude, a.longitude
                    from bookings b
                    left join user_addresses a
                    on b.user_id = a.user_id and b.addr_idx = a.user_addr_index'''
        if request_id == '':
            sql += ''' where (b.cleaning_status = 0) '''
        else:
            sql += ''' where (b.cleaning_status = 0 and b.request_id <> :request_id) '''
            query_param['request_id'] = request_id
        sql +=  ''') t
                on t.master_id = s.master_id and s.date = date(t.start_time)
                join master_prefered_area pa
                on pa.master_id = s.master_id and pa.prefered_gu = :gu_id
                where s.date >= :start_date and s.date <= :end_date and s.active = 1 {}
                order by s.master_id, s.date, start_time'''

        if master_id == '':
            sql = sql.format('')
        else:
            sql = sql.format('and s.master_id = :master_id')
            query_param['master_id'] = master_id

        occupied_slots = []

        try:
            session = Session()
            result = session.execute(sql, query_param).fetchall()

            for row in result:
                occupied_slots.append(dict(row))

        except Exception, e:
            print_err_detail(e)
            return []
        finally:
            session.close()

        return occupied_slots


    def get_available_slots(self, gu_id, geohash, appointment_type, taking_time, prefer_women, have_pet,
                                    isdirty, update = False, appointment_date = None,
                                    apply_to_all_behind = 0, user_id = '', master_id = '', by_manager = 0, request_id = ''):
        try:
            available_master_schedules_dict = {}

            #print gu_id, type(gu_id)
            #if gu_id == 2122010 or gu_id == 2157010 or gu_id == 2158050 or gu_id == 2152020: # 은평구, 강서구, 구로구 막기
            #    return {}
            masterdao = MasterDAO()
            userdao = UserDAO()

            available_start_date = 1
            available_end_date   = HMScheduler.DAYS_OF_WEEK * 3 - 1 # 3 weeks ahead
            all_end_date         = HMScheduler.DAYS_OF_WEEK * 11    # 2 months

            start_date = dt.datetime.now()

            if update == True:
                if appointment_type in [BC.ONE_TIME_A_MONTH, BC.TWO_TIME_A_MONTH, BC.FOUR_TIME_A_MONTH]:
                    start_date = appointment_date

                    available_start_date = -1 * HMScheduler.DAYS_OF_WEEK * (4 / appointment_type) + 1
                    available_end_date   = HMScheduler.DAYS_OF_WEEK * (4 / appointment_type * 2) - 2
                    all_end_date         = HMScheduler.DAYS_OF_WEEK * ((4 / appointment_type) + 8) - 1
                else:
                    available_start_date = 1
                    if by_manager == 1: # manager가 변경한 경우
                        available_start_date = 0
                    available_end_date   = HMScheduler.DAYS_OF_WEEK * 3 - 1 # 3 weeks ahead
                    all_end_date         = HMScheduler.DAYS_OF_WEEK * 11    # 2 months

            tomorrow = start_date + dt.timedelta(days = available_start_date)
            tomorrow = tomorrow.date()

            cur_date = tomorrow
            max_date = tomorrow + dt.timedelta(days = available_end_date) # 3 weeks ahead

            tomorrow_key = dt.datetime.strftime(tomorrow, '%Y%m%d')
            max_date_key = dt.datetime.strftime(max_date, '%Y%m%d')

            print 'date_keys'
            print tomorrow_key, max_date_key

            occupied_slots = self.get_occupied_slots(gu_id, appointment_type, by_manager, cur_date, cur_date + dt.timedelta(days = all_end_date),
                                                    prefer_women, have_pet, master_id, request_id)

            if isdirty == True and not appointment_type in [BC.ONE_TIME_A_MONTH, BC.TWO_TIME_A_MONTH, BC.FOUR_TIME_A_MONTH]:
                taking_time += 120 # if it is dirty then add two hours

            # find any free slots based on hours required for cleaning for 10 weeks
            while cur_date <= tomorrow + dt.timedelta(days=all_end_date): # 11 weeks
                daily_available_schedule_dict = self.get_available_slots_for_day(geohash, cur_date, taking_time, occupied_slots, isdirty, by_manager)
                available_master_schedules_dict[self.date_to_str(cur_date)] = daily_available_schedule_dict

                cur_date += dt.timedelta(days=1)

            available_master_schedules_dict = collections.OrderedDict(sorted(available_master_schedules_dict.items(), key=lambda x: x[0]))

            print 'appointment_type', appointment_type

            # if update only one schedule, then don't have to check rest of the schedules
            if update == True and apply_to_all_behind == 0:
                appointment_type = 0

            # if appointment_type > 0, then we should find out days that would be free for number of iteration
            if appointment_type in [BC.ONE_TIME_A_MONTH, BC.TWO_TIME_A_MONTH, BC.FOUR_TIME_A_MONTH]:
                for day in available_master_schedules_dict: # each day
                    if day > max_date_key: break

                    for master_id in available_master_schedules_dict[day]: # each master
                        #completed_cnt = masterdao.get_master_completed_cleaning_count(master_id)
                        #if completed_cnt <= 5: # 횟수가 5회를 넘지 않은 마스터는
                        #    continue

                        iter_available_times = []
                        iter_available_times.append(available_master_schedules_dict[day][master_id])

                        iter_count = self.count_of_iteration(appointment_type)

                        for i in xrange(iter_count-1):
                            next_date = dt.datetime.strptime(day, '%Y%m%d') + dt.timedelta(weeks = (4 / appointment_type) * (i+1))
                            next_date = dt.datetime.strftime(next_date, '%Y%m%d')

                            if next_date in available_master_schedules_dict:
                                if master_id in available_master_schedules_dict[next_date]:
                                    iter_available_times.append(available_master_schedules_dict[next_date][master_id])

                        reduced = func.reduce(np.intersect1d, iter_available_times)
                        new_available_times = reduced
                        if not isinstance(reduced, list): # sometimes it returns list
                            new_available_times = reduced.tolist()
                        available_master_schedules_dict[day][master_id] = new_available_times

            # filter by duration (two weeks ahead from tomorrow)
            available_master_schedules_dict = dict((key, value)
                                                for key, value in available_master_schedules_dict.iteritems()
                                                if tomorrow_key <= key <= max_date_key)


            blocked_masters = userdao.get_blocked_masters(user_id)

            print 'blocked masters'
            print blocked_masters

            master_rating_dict = {}
            # rebuild dictionary by time value
            for day in available_master_schedules_dict:
                day_schedule_dict = available_master_schedules_dict[day]

                # convert master_id key to time key
                new_schedule_dict = {}
                for master_id in day_schedule_dict:
                    if master_id in blocked_masters:
                        continue

                    available_times = day_schedule_dict[master_id]
                    available_times_num = len(available_times)

                    if not master_id in master_rating_dict:
                        avg_rating = masterdao.get_avg_master_cleaning_rating(master_id)
                        master_rating_dict[master_id] = avg_rating

                    for time in available_times:
                        #time = self.time_to_str(time) # convert nptime to string
                        #score_criteria = (master_id, (1.0 / available_times_num), master_rating_dict[master_id])
                        score_criteria = (master_id, 1, master_rating_dict[master_id])

                        if not time in new_schedule_dict:
                            new_schedule_dict[time] = []
                            new_schedule_dict[time].append(score_criteria)
                        else:
                            new_schedule_dict[time].append(score_criteria)

                # sort by scoring criteria
                for time in new_schedule_dict:
                    scored_master_ids = [item[0] for item in sorted(new_schedule_dict[time], key = operator.itemgetter(1, 2), reverse = True)]
                    new_schedule_dict[time] = ','.join(scored_master_ids)
                    #new_schedule_dict[time] = sorted(new_schedule_dict[time], key = operator.itemgetter(1, 2), reverse = True)

                new_schedule_dict = collections.OrderedDict(sorted(new_schedule_dict.items(), key=lambda x: x[0])) # sort by time key

                #available_master_schedules_dict[day]['by_master']   = day_schedule_dict
                available_master_schedules_dict[day]['by_time']     = new_schedule_dict
                available_master_schedules_dict[day]['time_list']   = new_schedule_dict.keys()

            ret_dict = {}

            for day in available_master_schedules_dict:
                day_schedule_dict = available_master_schedules_dict[day]

                if len(day_schedule_dict['time_list']) > 0: # 가능한 날짜만 보냄.
                    ret_dict[day] = {}
                    ret_dict[day]['by_time'] = day_schedule_dict['by_time']
                    ret_dict[day]['time_list'] = day_schedule_dict['time_list']

            ret_dict = collections.OrderedDict(sorted(ret_dict.items(), key=lambda x: x[0])) # sort by date key

            return ret_dict

        except Exception, e:
            print_err_detail(e)
            return {}


    # Find all possible time gaps inside particular day
    def get_available_slots_for_day(self, geohash, cur_date, taking_time, occupied_slots, isdirty, by_manager = 0):
        masters = {}

        now = dt.datetime.now()
        if by_manager == 1:
            now -= dt.timedelta(days=1) # 매니저가 변경하는 경우는, 오늘날짜도 변경 가능하도록 수정

        now = dt.datetime.strftime(now, '%Y%m%d')

        if dt.datetime.strftime(cur_date, '%Y%m%d') <= now:
            return masters

        # 설날 방지
        #if dt.datetime.strftime(cur_date, '%Y%m%d') in ['20160207', '20160208', '20160209', '20160210']:
        #    return masters

        # 2016 추석 방지
        #if dt.datetime.strftime(cur_date, '%Y%m%d') in ['20160914', '20160915', '20160916']:
        #    return masters

        if dt.datetime.strftime(cur_date, '%Y%m%d') in ['20170127', '20170128', '20170129']:
            return masters

        today_occupied_slots = filter(lambda x : x['date'] == cur_date, occupied_slots)

        # build occupied time slots by master_id
        for slot in today_occupied_slots:
            try:
                master_id = slot['master_id']
            except Exception, e:
                print_err_detail(e)
                continue

            if master_id in masters:
                masters[master_id]['occupied_times'].append([self.to_nptime(slot['start_time']), self.to_nptime(slot['end_time']), slot['geohash6']])
            else:
                masters[master_id] = {}
                masters[master_id]['free_from']      = self.to_nptime(slot['free_from'])
                masters[master_id]['free_to']        = self.to_nptime(slot['free_to'])

                masters[master_id]['occupied_times'] = []
                if slot['start_time'] != None:
                    masters[master_id]['occupied_times'].append([self.to_nptime(slot['start_time']), self.to_nptime(slot['end_time']), slot['geohash6']])

        # build available time slots by master_id
        for master_id in masters:
            try:
                master = masters[master_id]
            except Exception, e:
                print_err_detail(e)
                continue

            try:
                master['occupied_times'].insert(0, [master['free_from'], master['free_from'], None])
                master['occupied_times'].append([master['free_to'], master['free_to'], None])
            except Exception, e:
                print_err_detail(e)
                continue

            master['available_times'] = []

            block_time_tables = []
            if by_manager == 0:
                block_time_tables = ['10:30', '11:00', '11:30', '12:00', '12:30']

            if len(master['occupied_times']) == 2: # free day

                cur_time = master['free_from']

                #if master_id == 'e1d543b5-a0d5-4ed0-b5db-24cf63db4453' and dt.datetime.strftime(cur_date, '%Y%m%d') == '20160603':
                    #print cur_date, cur_time

                while dt.datetime.combine(cur_date, cur_time) + dt.timedelta(minutes = taking_time) <= dt.datetime.combine(cur_date, master['free_to']): # add available time list
                #while cur_time + dt.timedelta(minutes = taking_time) <= master['free_to']: # add available time list
                    str_cur_time = self.time_to_str(cur_time)
                    if str_cur_time not in block_time_tables:
                        master['available_times'].append(str_cur_time) # for json serialization
                    cur_time += dt.timedelta(minutes = 30)

                    #if master_id == 'e1d543b5-a0d5-4ed0-b5db-24cf63db4453' and dt.datetime.strftime(cur_date, '%Y%m%d') == '20160603':
                        #print cur_date, cur_time
            else:
                for i, slot in enumerate(master['occupied_times']):
                    time1 = slot[1]
                    time2 = master['occupied_times'][i+1][0] if i + 1 < len(master['occupied_times']) else master['free_to']

                    if time2 > time1 and time_to_minutes(timedelta_to_time(time2 - time1)) > taking_time:
                        geohash1 = slot[2]
                        geohash2 = master['occupied_times'][i+1][2] if i + 1 < len(master['occupied_times']) else None

                        moving_time1 = get_moving_time(geohash1, geohash)
                        moving_time2 = get_moving_time(geohash2, geohash)

                        # 앞 뒤 2시간 이상이 걸리거나, 합계로 150분 초과로 걸리는 것 상황은 일을 배정하지 않는다.
                        #if moving_time1 >= 120 or moving_time2 >= 120 or moving_time1 + moving_time2 > 150:
                        #    continue

                        cur_time = time1 + dt.timedelta(minutes = moving_time1)

                        while dt.datetime.combine(cur_date, cur_time) + dt.timedelta(minutes = taking_time + moving_time2) <= dt.datetime.combine(cur_date, time2): # add available time list
                            str_cur_time = self.time_to_str(cur_time)
                            if str_cur_time not in block_time_tables:
                                master['available_times'].append(str_cur_time) # for json serialization
                            cur_time += dt.timedelta(minutes = 30)

            del master['free_from']
            del master['free_to']
            del master['occupied_times']

            masters[master_id] = master['available_times']

        return masters


    def count_of_iteration(self, appointment_type):
        # 4 times a month -> 9
        # 2 times a month -> 5
        # 1 times a momth -> 3
        # two months of appointment
        return appointment_type * 2 + 1


    def to_nptime(self, time):
        time = timedelta_to_time(time)
        return nptime(time.hour, time.minute)


    def date_to_str(self, date):
        return dt.datetime.strftime(date, '%Y%m%d')


    def time_to_str(self, time):
        return time.strftime('%H:%M')




if __name__ == '__main__':
    obj = HMScheduler()

    tomorrow = dt.datetime.now() + dt.timedelta(days=1)
    tomorrow = tomorrow.date()
    cur_date = tomorrow
    import time

    start = time.time()
    available_schedules = obj.get_available_slots('2135010', 'wydm68', 2, 300, True, False, False)
    taking_time = time.time() - start

    '''for s in available_schedules:
        print s
        print available_schedules[s]['time_list']
        print available_schedules[s]['by_time']

            #assert len(available_schedules[s]['by_time'][time]) == 2
            #print available_schedules[s]['by_master']'''

    print available_schedules
    print taking_time
