#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

from datetime import datetime
from datetime import date
from datetime import timedelta
from datetime import time
from nptime   import nptime

import calendar

from err.error_handler import print_err_detail, err_dict


def get_month_day_range(date):
    first_day = date.replace(day = 1)
    last_day = date.replace(day = calendar.monthrange(date.year, date.month)[1])
    return first_day, last_day

def ceil_datetime(dt):
    temp = dt + timedelta(hours=2)
    new_dt = datetime(temp.year, temp.month, temp.day, temp.hour, 00, 0)
    return new_dt

def floor_datetime(dt):
    pass

def convert_time_format(time):
    try:
        ampm = {'AM' : '오전', 'PM' : '오후'}

        ampmpart = ampm[time.strftime('%p')]
        timepart = time.strftime('%I:%M')

        return '%s %s' % (ampmpart, timepart)
    except Exception, e:
        print_err_detail(e)
        return time.strftime('%H:%M')

def convert_datetime_format(date):
    try:
        dows = {'Mon' : '월요일', 'Tue' : '화요일', 'Wed' : '수요일', 'Thu' : '목요일', 'Fri' : '금요일', 'Sat' : '토요일', 'Sun' : '일요일'}
        ampm = {'AM' : '오전', 'PM' : '오후'}

        datepart = date.strftime('%Y년 %m월 %d일')
        dowpart  = dows[date.strftime('%a')]
        ampmpart = ampm[date.strftime('%p')]
        timepart = date.strftime('%I:%M')

        return '%s %s %s %s' % (datepart, dowpart, ampmpart, timepart)
    except Exception, e:
        print_err_detail(e)
        return date.strftime('%Y년 %m월 %d일 %H:%M')


def convert_datetime_format2(date):
    try:
        dows = {'Mon' : '월요일', 'Tue' : '화요일', 'Wed' : '수요일', 'Thu' : '목요일', 'Fri' : '금요일', 'Sat' : '토요일', 'Sun' : '일요일'}
        ampm = {'AM' : '오전', 'PM' : '오후'}

        datepart = date.strftime('%Y년 %m월 %d일')
        dowpart  = dows[date.strftime('%a')]
        ampmpart = ampm[date.strftime('%p')]
        timepart = date.strftime('%-I시 %-M분')

        return '%s %s %s %s' % (datepart, dowpart, ampmpart, timepart.replace(' 0분', ''))
    except Exception, e:
        print_err_detail(e)
        return date.strftime('%Y년 %m월 %d일 %H시%M')

def convert_datetime_format3(date):
    try:
        dows = {'Mon' : '월', 'Tue' : '화', 'Wed' : '수', 'Thu' : '목', 'Fri' : '금', 'Sat' : '토', 'Sun' : '일'}
        ampm = {'AM' : '오전', 'PM' : '오후'}

        datepart = date.strftime('%-m/%d')
        dowpart  = dows[date.strftime('%a')]
        ampmpart = ampm[date.strftime('%p')]
        timepart = date.strftime('%-I시 %-M분')

        return '%s(%s) %s %s 클리닝' % (datepart, dowpart, ampmpart, timepart.replace(' 0분', ''))
    except Exception, e:
        print_err_detail(e)
        return date.strftime('%Y년 %m월 %d일 %H시%M')


def convert_datetime_format4(date):
    try:
        dows = {'Mon' : '월', 'Tue' : '화', 'Wed' : '수', 'Thu' : '목', 'Fri' : '금', 'Sat' : '토', 'Sun' : '일'}
        ampm = {'AM' : '오전', 'PM' : '오후'}

        ampmpart = ampm[date.strftime('%p')]
        timepart = date.strftime('%-I시 %-M분')

        return '오늘 %s %s' % (ampmpart, timepart.replace(' 0분', ''))
    except Exception, e:
        print_err_detail(e)
        return ''



def timedelta_to_time(td):
    try:
        if td == None: return None
        return (datetime.min + td).time()
    except Exception ,e:
        print_err_detail(e)
        return time(0, 0)


def time_to_minutes(t):
    try:
        return t.hour * 60 + t.minute
    except Exception, e:
        print_err_detail(e)
        return 0

def time_to_str(t):
    return t.strftime('%H%M')

def time_to_str2(t):
    return t.strftime('%H:%M')


def time_added_minute(t, minute):
    return (datetime.combine(date(2015, 1, 1), t) + timedelta(minutes=minute)).time()


def time_substracted_minute(t, minute):
    return (datetime.combine(date(2015, 1, 1), t) - timedelta(minutes=minute)).time()

def dow_convert(date1,date2):

    day_diff = date2.weekday() - date1.weekday()
    return date1 + timedelta(days = day_diff)
def date_convert(date1,date_diff):

    return date1 + date_diff
if __name__ == '__main__':
    #print ceil_datetime(datetime.now())

    a = nptime(15, 30)
    b = nptime(15, 40)

    print time_to_minutes(timedelta_to_time(a - b))
