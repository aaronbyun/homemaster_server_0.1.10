#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

WEEKEND_ADDED_SALARY = 8000

WEEKDAYS             = [0, 1, 2, 3, 4]
WEEKEND              = [5, 6]

DAYS_IN_A_WEEK = 7

START_TIME_RANGE_BEGIN = 8
START_TIME_RANGE_END = 18

SALARY_FOR_SMALL_IN_HOUR = 1400 # 12000원이나 계산 용이를 위해 1200으로 둠
SALARY_FOR_NORMAL_IN_HOUR = 1200 # 14000원이나 계산 용이를 위해 1200으로 둠(작은 평수에 대해서 이렇게 처리함)

SALARY_FOR_ONETIME_IN_HOUR = 1200 # 12000원이나 계산 용이를 위해 1200으로 둠 (1회)
SALARY_FOR_REGULAR_IN_HOUR = 1140 # 11400원이나 계산 용이를 위해 1140으로 둠 (정기의 경우)

ONE_TIME                    = 0
ONE_TIME_A_MONTH            = 1
TWO_TIME_A_MONTH            = 2
ONE_TIME_BUT_CONSIDERING    = 3
FOUR_TIME_A_MONTH           = 4

# for b2b 2 months
ONE_TIME_TWO_MONTH          = 8

REGULAR_CLEANING_DICT = {FOUR_TIME_A_MONTH : 1, TWO_TIME_A_MONTH : 1}

# BOOKING REQUEST STATUS
BOOKING_REQUEST_CANCELED    = -1
BOOKING_REQUEST_REQUESTED   = 0
BOOKING_REQUEST_BOOKED      = 1

# CLEANING STATUS
BOOKING_UPCOMMING           = 0
BOOKING_STARTED             = 1
BOOKING_COMPLETED           = 2
BOOKING_CANCELED            = -1

#PAYMENT STATUS
BOOKING_PAYMENT_FAILED      = -3
BOOKING_CANCELED_CHARGE     = -2
BOOKING_CANCELED_REFUND     = -1
BOOKING_UNPAID_YET          = 0
BOOKING_PAID                = 1

# CHARGE RATE
BOOKING_CHARGE_RATE_NO      = 0.0
BOOKING_CHARGE_RATE_30      = 0.3
BOOKING_CHARGE_RATE_50      = 0.5
BOOKING_CHARGE_RATE_70      = 0.7
BOOKING_CHARGE_RATE_ALL     = 0.5

VACCUM_CHARGE = 4000


bank_dict  = {}
bank_dict[u'KDB산업']  = 2
bank_dict[u'IBK기업']  = 3
bank_dict[u'KB국민']   = 4
bank_dict[u'외환은행']  = 5
bank_dict[u'수협은행']  = 7
bank_dict[u'NH농협']   = 11
bank_dict[u'우리은행']  = 20
bank_dict[u'SC은행']   = 23
bank_dict[u'신한은행']  = 26
bank_dict[u'씨티은행']  = 27
bank_dict[u'대구은행']  = 31
bank_dict[u'부산은행']  = 32
bank_dict[u'광주은행']  = 34
bank_dict[u'제주은행']  = 35
bank_dict[u'전북은행']  = 37
bank_dict[u'경남은행']  = 39
bank_dict[u'새마을은행'] = 45
bank_dict[u'신협은행']  = 48
bank_dict[u'저축은행']  = 50
bank_dict[u'산림조합']  = 64
bank_dict[u'우체국']    = 71
bank_dict[u'하나은행']  = 81
