#-*- coding: utf-8 -*-

import tornado.ioloop
import tornado.web
import tornado.httpserver
import json
from pymongo import MongoClient


from admin.master_schedule_time_handler import MasterScheduleTimeOnDateInfoHandler
from master.master_salary_period_handler import MasterSalaryPeriodHandler
from master.all_weekly_salary_handler import AllWeeklySalaryHandler
from master.master_new_all_weekly_salary_handler import NewAllWeeklySalaryHandler
from master.master_rating_history_handler import MasterRatingHistoryHandler
from master.master_monthly_salary_handler import MasterMonthlySalaryHandler
from master.master_all_monthly_salary_handler import MasterAllMonthlySalaryHandler

from management.monthly_revenue_handler import MonthlyRevenueHandler
from management.weekly_maximum_available_schedules_handler import WeeklyMaximumAvailableScheduleHandler
from management.get_user_in_funnel_handler import UserInFunnelHandler
from management.user_contact_record_handler import UserContactRecordHandler

from booking_11st_new.complete_payment_11st_booking_handler import Complete11stPaymentBookingHandler
from booking_11st_new.complete_service_handler import CompleteService11stHandler
from booking_11st_new.link_hm_11st_booking_handler import LinkHomemaster11stBookingHandler

try:
    from utils.secrets import MONGO_HOST, MONGO_PORT
except ImportError:
    MONGO_HOST = 'localhost'
    DB_PORT = 27017

mongo = MongoClient(MONGO_HOST, MONGO_PORT)

application = tornado.web.Application([
    (r'/hm_schedule_ondate', MasterScheduleTimeOnDateInfoHandler),
    (r'/all_weekly_salary', NewAllWeeklySalaryHandler),
    (r'/all_monthly_salary', MasterAllMonthlySalaryHandler),

    (r'/monthly_revenue', MonthlyRevenueHandler),
    (r'/weekly_maximum_available', WeeklyMaximumAvailableScheduleHandler),
    (r'/user_in_funnel', UserInFunnelHandler),
    (r'/user_contact_reason', UserContactRecordHandler),

    (r'/get_payment_done_11st', Complete11stPaymentBookingHandler),
    (r'/finish_11st_cleaning', CompleteService11stHandler),
    (r'/link_11st_hm', LinkHomemaster11stBookingHandler)

    ], autoreload=True)
