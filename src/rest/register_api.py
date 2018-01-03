#-*- coding: utf-8 -*-

import tornado.ioloop
import tornado.web
import tornado.httpserver
import json
from pymongo import MongoClient

from search_address.residence_handler import ResidenceHandler
from search_address.address_handler import AddressHandler
from search_address.search_doro_address_handler_new import DoroAddressSearchHandler

from user.register_handler import RegisterHandler
from user.userinfo_handler import UserInfoHandler
from user.salt_handler import SaltHandler
from user.login_handler import LoginHandler
from user.fb_login_handler import FBLoginHandler
from user.add_address_handler import AddAddressHandler
from user.default_address import DefaultAddressHandler
from user.password_handler import PasswordHandler
from user.pushkey_handler import PushkeyHandler
from user.user_memo_handler import UserMemoHandler
from user.modify_address_handler import ModifyAddressHandler
from user.modify_address_by_index_handler import ModifyAddressByIndexHandler
from user.faq_handler import FAQHandler
from user.faq_master_handler import FAQMasterHandler
from user.modify_userinfo_handler import ModifyUserInfoHandler
from user.remove_address_handler import RemoveAddressHandler
from user.reset_password_handler import ResetPwdHandler
from user.user_card_handler import UserCardHandler
from user.delete_user_handler import DeleteUserHandler
from user.modify_address_booking_handler import ModifyAddressBookingHandler
from user.user_all_address_handler import UserAllAddressHandler
from user.user_payment_history_handler import UserPaymentHistoryHandler
from user.request_user_coupon_handler import RequestUserCouponHandler
from user.apply_user_coupon_handler import ApplyUserCouponHandler
from user.register_web_handler import RegisterWebHandler
from user.login_web_handler import LoginWebHandler
from user.set_default_card_handler import SetDefaultCardHandler
from user.user_event_log_handler import UserEventLogHandler
from user.user_payment_charge_history_handler import UserPaymentChargeHistoryHandler
from user.test_process_handler import TestProcessHandler
from user.user_address_info_handler import UserAddressInfoHandler


#from booking.schedule_handler import ScheduleHandler
from booking.request_booking_handler import RequestBookingHandler
from booking.request_booking_for_manager_handler import RequestBookingForManagerHandler
from booking.rate_handler import RatingHandler
from booking.mybookings_handler import MyBookingsHandler
from booking.mybookings_detail_handler import MyBookingsDetailHandler
from booking.edit_booking_handler import EditBookingHandler
from booking.edit_available_handler import EditAvailableHandler
from booking.cancel_booking_handler import CancelBookingHandler
from booking.cancel_all_booking_handler import CancelAllBookingHandler
from booking.recommend_schedule_handler import ScheduleRecommendHandler
from booking.master_handler import MasterHandler
from booking.recommend_no_handler import RecommendNoHandler
from booking.booking_add_extrainfo_handler import AddBookingExtraInfoHandler
from booking.request_schedule_handler import RequestScheduleHandler
from booking.apply_promotion_code_handler import ApplyPromotionCodeHandler
from booking.apply_promotion_code_upcoming_booking_handler import ApplyPromotionCodeToUpComingBookingHandler
from booking.notify_when_service_available_handler import NotifyServiceAvailabilityHandler
from booking.cancel_charge_handler import CancelChargeHandler
from booking.cancel_booking_for_manager_handler import CancelBookingForManagerHandler
from booking.cancel_all_booking_for_manager_handler import CancelAllBookingForManagerHandler
from booking.edit_booking_for_manager_handler import EditBookingForManagerHandler
from booking.master_gender_by_region_handler import MasterGenderByRegionHandler
from booking.registercard_handler import RegisterCardHandler
from booking.dummy_handler import DummyHandler
from booking.price_handler import PriceHandler
from booking.request_available_schedule_handler import RequestAvailableSchedulesHandler
from booking.request_available_schedule_for_update_handler import RequestAvailableSchedulesForUpdateHandler
from booking.request_available_schedules_for_change_circle_handler import RequestAvailableSchedulesForChangeCircleHandler
from booking.change_circle_handler import ChangeCircleHandler
from booking.request_select_schedule_handler import RequestSelectScheduleHandler
from booking.request_select_schedule_web_handler import RequestSelectScheduleWebHandler
from booking.request_confirm_schedule_handler import RequestConfirmScheduleHandler
from booking.request_confirm_schedule_for_manager_handler import RequestConfirmScheduleForManagerHandler
from booking.update_additional_task_handler import UpdateAdditionalTaskHandler
from booking.update_schedule_handler import UpdateScheduleHandler
from booking.update_schedule_handler2 import UpdateScheduleHandler2
from booking.request_charge_handler import RequestChargeHandler
from booking.my_allbookings_handler import MyAllBookingsHandler
from booking.delay_30_handler import Delay30Handler
from booking.modify_additional_task_handler import ModifyAdditionalTaskHandler
from booking.request_time_price_handler import RequestTimePriceHandler
from booking.request_available_schedule_for_adminweb_handler import RequestAvailableSchedulesForAdminWebHandler
from booking.request_select_schedule_for_adminweb_handler import RequestSelectSchedulesForAdminWebHandler
from booking.request_time_price_web_handler import RequestTimePriceWebHandler
from booking.request_available_schedule_web_handler import RequestAvailableSchedulesWebHandler
from booking.request_confirm_schedule_web_handler import RequestConfirmScheduleWebHandler
from booking.request_all_time_price_handler import RequestAllTimePriceHandler
from booking.request_confirm_schedule_adminweb_handler import RequestConfirmScheduleAdminWebHandler
from booking.apply_coupon_handler import ApplyCouponHandler
from booking.apply_cancel_coupon_handler import ApplyCancelCouponHandler
from booking.booking_charge_handler import BookingChargeHandler
from booking.request_confirm_schedule_new_handler import RequestConfirmScheduleNewHandler
from booking.payment_status_handler import PaymentStatusHandler
from booking.cleaning_status_handler import CleaningStatusHandler
# 11 street
from booking_11.request_available_schedule_11_handler import RequestAvailableSchedules11stHandler
from booking_11.request_select_schedule_11_handler import RequestSelectSchedule11stHandler


from admin.all_users_info_handler import AllUserInfoHandler
from admin.all_masters_info_handler import AllMasterInfoHandler
from admin.master_info_handler import MasterInfoHandler
from admin.master_schedule_time_handler import MasterScheduleTimeOnDateInfoHandler
from admin.auto_register_booking_handler import AutoRegisterBookingHandler
from admin.master_add_handler import MasterAddHandler
from admin.master_update_basic_handler import MasterUpdateBasicHandler
from admin.master_update_time_handler import MasterUpdateTimeHandler
from admin.master_update_area_handler import MasterUpdateAreaHandler
from admin.master_delete_handler import MasterDeleteHandler
from admin.master_schedule_change_handler import ChangeMasterOnScheduleHandler
from admin.master_schedule_all_change_handler import ChangeMasterOnAllScheduleHandler
from admin.master_salary_handler import MasterSalaryOnDateHandler
from admin.all_managers_info_handler import AllManagerInfoHandler
from admin.manager_info_handler import ManagerInfoHandler
from admin.manager_add_handler import ManagerAddHandler
from admin.manager_update_handler import ManagerUpdateHandler
from admin.booking_info_handler import BookingInfoHandler
from admin.register_user_and_booking_handler import RegisterUserAndBookingHandler
from admin.promotion_codes_handler import ManagePromotionCodeHandler
from admin.user_memo_info_handler import MemoInfoHandler
from admin.process_user_memo_handler import ProcessUserMemoHandler
from admin.unmatched_booking_handler import UnMatchedBookingHandler
from admin.schedule_complete_handler import ScheduleCompleteHandler
from admin.schedule_paid_handler import SchedulePaidHandler
from admin.schedule_start_handler import ScheduleStartHandler
from admin.schedule_start_with_time_handler import ScheduleStartWithTimeHandler
from admin.payment_history_handler import PaymentHistoryHandler
from admin.manual_charge_handler import ManualChargeHandler
from admin.charge_handler import ChargeHandler
from admin.all_paid_bookings_info_handler import AllPaidBookingInfoHandler
from admin.all_bookings_handler import AllBookingInfoHandler
from admin.all_ratings_info_handler import AllRatingInfoHandler
from admin.master_avg_rating_handler import MasterAvgRatingHandler
from admin.schedule_complete_with_time_handler import ScheduleCompleteWithTimeHandler
from admin.master_notification_content_handler import MasterNotificationContentHandler
from admin.modify_entrance_method_handler import ModifyEntranceMethodHandler
from admin.modify_master_gender_handler import ModifyMasterGenderHandler
from admin.modify_msg_handler import ModifyMsgHandler
from admin.homemaster_stats_handler import HomemasterStatInfoHandler
from admin.users_info_handler import UserSearchHandler
from admin.manual_unpaid_charge_handler import ManualUnpaidChargeHandler
from admin.get_users_not_request_booking_handler import UserNotRequestBookingHandler
from admin.get_users_groupAB_handler import UserGroupABHandler
from admin.policy_handler import PolicyHandler
from admin.all_memos_handler import AllMemoInfoHandler
from admin.ios_customer_handler import IOSNoneCustomerHandler

from master.master_login_handler import MasterLoginHandler
from master.master_schedule_ondate_handler import MasterScheduleOnDateHandler
from master.master_set_password_handler import MasterSetPasswordHandler
from master.master_check_password_handler import MasterCheckPasswordHandler
from master.master_salary_handler import MasterSalaryHandler
from master.master_salary_period_handler import MasterSalaryPeriodHandler
from master.all_weekly_salary_handler import AllWeeklySalaryHandler
from master.master_add_point_handler import MasterPointAddHandler
from master.master_point_description_handler import MasterPointDescriptionHandler
from master.master_point_total_handler import MasterPointTotalHandler
from master.master_point_detail_handler import MasterPointDetailHandler
from master.master_work_list_handler import MasterWorkListHandler
from master.master_rating_history_handler import MasterRatingHistoryHandler
from master.master_working_date_handler import MasterWorkDateHandler
from master.master_routing_guide_handler import MasterRoutingGuideHandler
from master.master_all_memos_handler import AllMasterMemoInfoHandler
from master.master_post_memo_handler import MasterPostMemoHandler
from master.master_pushkey_handler import MasterPushkeyHandler
from master.master_post_claim_handler import MasterClaimHandler
from master.master_all_claim_handler import MasterAllClaimHandler
from master.master_new_all_weekly_salary_handler import NewAllWeeklySalaryHandler
from master.master_new_salary_handler import NewMasterSalaryHandler
from master.master_names_handler import MasterNamesHandler
from master.master_weekly_detail_salary_handler import MasterWeeklyDetailSalaryHandler
from master.master_modify_alergy_handler import MasterModifyAlergyStateHandler
from master.master_remove_handler import MasterRemoveHandler
from master.all_master_name_handler import AllMasterNameHandler
from master.master_add_account_handler import MasterAddAccountHandler
from master.register_master_handler import RegisterMasterHandler
from master.master_reset_password_handler import MasterResetPasswordHandler
from master.get_master_names_handler import GetMasterNamesHandler
from master.master_monthly_salary_handler import MasterMonthlySalaryHandler
from master.master_all_monthly_salary_handler import MasterAllMonthlySalaryHandler
from master.notify_homemaster_handler import NotifyHomemasterHandler
from master.apply_homemaster_handler import ApplyHomemasterHandler
from master.master_add_prize_handler import MasterAddPrizeHandler
from master.master_prize_handler import MasterPrizeHandler
from master.master_reset_prize_handler import MasterResetPrizeHandler
from master.master_penalty_handler import MasterPenaltyHandler
from master.master_charge_penalty_handler import MasterChargePenaltyHandler
from master.master_penalty_accumulate_handler import MasterPenaltyAccumulateHandler
from master.extra_minutes_handler import ExtraMinutesHandler
from master.master_notice_handler import MasterNoticeHandler
from master.master_notice_edit_handler import MasterNoticeEditHandler
from master.master_notice_remove_handler import MasterNoticeRemoveHandler

from skt.tapi_handler import TAPIHandler

from admin_new.search_userinfo_handler import SearchUserInfoHandler
from admin_new.claim_input_handler import ClaimInputHandler
from admin_new.claim_search_handler import ClaimSearchHandler
from admin_new.unpaid_list_handler import UnpaidListHandler
from admin_new.modify_rate_handler import ModifyRateHandler
from admin_new.booking_change_history_handler import BookingChangeHistoryHandler
from admin_new.unassigned_bookings_handler import UnassignedBookingsHandler
from admin_new.remove_unassigned_bookings_handler import RemoveUnassignedBookingsHandler
from admin_new.master_booking_modify_request_handler import MasterBookingModifyRequestHandler
from admin_new.master_dayoff_request_handler import MasterDayoffRequestHandler
from admin_new.master_dayoff_cancel_handler import MasterDayoffCancelHandler
from admin_new.master_monthly_modify_request_count_handler import MasterMonthlyRequestCountHandler
from admin_new.notice_sms_handler import NoticeSMSHandler
from admin_new.input_admin_memo_handler import InputAdminMemoHandler
from admin_new.request_admin_memo_handler import RequestAdminMemoHandler
from admin_new.check_bank_account_handler import CheckBankAccountHandler
from admin_new.discount_upcoming_cleaning_handler import DiscountUpcomingCleaningHandler
from admin_new.cancel_payment_handler import CancelPaymentHandler
from admin_new.search_masterinfo_handler import SearchMasterInfoHandler
from admin_new.create_user_coupon_handler import CreateUserCouponHandler
from admin_new.input_master_notice_handler import InputMasterNoticeHandler
from admin_new.request_master_notices_handler import RequestMasterNoticesHandler
from admin_new.request_user_coupon_adminweb_handler import RequestUserCouponAdminWebHandler
from admin_new.user_registerinfo_handler import UserRegisterInfoHandler

from moving.mv_notify_manager_handler import MovingCleaningNotifyManagerHandler

from management.version_check_handler import VersionHandler
from management.weekly_revenue_handler import WeeklyRevenueHandler
from management.indicator_handler import WeeklyIndicatorHandler
from management.reject_relation_handler import RejectRelationHandler
from management.user_reject_relation_handler import UserRejectRelationHandler
from management.monthly_revenue_handler import MonthlyRevenueHandler

from master.get_youtube_content_handler import GetYouTubeContentHandler
from master.modify_account_no_handler import ModifyAccountNoHandler

from office.inquery_office_cleaning_handler import InqueryOfficeCleaningHandler

from unpaid.check_unpaid_booking_handler import CheckUnpaidBookingHandler
from unpaid.process_unpaid_booking_handler import ProcessUnpaidBookingHandler

from event.get_active_event_handler import ActiveEventHandler
from event.event_freeonetime_handler import FreeOneTimeRegularCleaningHandler

from checklist.submit_checklist_handler import SubmitChecklistHandler
from checklist.user_check_list_handler import UserChecklistHandler

from new_web.cleaning_handler import CleaningHandler
from new_web.process_cleaning_handler import ProcessCleaningHandler
from new_web.register_and_charge_handler import RegisterCardAndChargeHandler
from new_web.request_cleaning_handler import RequestCleaningHandler
from new_web.select_payment_method_handler import SelectPaymentMethodHandler
from new_web.check_my_cleaning_handler import CheckMyCleaningHandler
from new_web.remove_cleaning_handler import RemoveCleaningHandler
from new_web.update_cleaning_status_handler import UpdateWebCleaningStatusHandler

from manager.regular_basis_user_manage_handler import RegularBasisUserManageHandler
from manager.update_rb_user_handler import UpdateRegularBasisUserHandler

try:
    from utils.secrets import MONGO_HOST, MONGO_PORT
except ImportError:
    MONGO_HOST = 'localhost'
    DB_PORT = 27017

mongo = MongoClient(MONGO_HOST, MONGO_PORT)

application = tornado.web.Application([
    (r'/residence', ResidenceHandler, dict(mongo=mongo)),
    (r'/address', AddressHandler, dict(mongo=mongo)),
    (r'/doro_address', DoroAddressSearchHandler),
    (r'/register', RegisterHandler),
    (r'/add_address', AddAddressHandler),
    (r'/modify_address', ModifyAddressHandler),
    (r'/modify_address_by_index', ModifyAddressByIndexHandler),
    (r'/set_default_address', DefaultAddressHandler),
    (r'/user_info', UserInfoHandler),
    (r'/login', LoginHandler),
    (r'/fblogin', FBLoginHandler),
    (r'/salt', SaltHandler),
    (r'/modifypwd', PasswordHandler),
    (r'/pushkey', PushkeyHandler),
    (r'/request_schedule', RequestScheduleHandler),
    (r'/request_booking', RequestBookingHandler),
    (r'/request_booking_for_manager', RequestBookingForManagerHandler),
    (r'/review', RatingHandler),
    (r'/memo', UserMemoHandler),
    (r'/mybookings/(?P<mode>[a-z]+)', MyBookingsHandler),
    (r'/my_all_bookings/(?P<mode>[a-z]+)', MyAllBookingsHandler),
    (r'/mybookings_detail', MyBookingsDetailHandler),
    (r'/cancel_booking', CancelBookingHandler),
    (r'/cancel_all_booking', CancelAllBookingHandler),
    (r'/recommend_schedule', ScheduleRecommendHandler),
    (r'/recommend_dismiss', RecommendNoHandler),
    (r'/schedule_dismiss', RecommendNoHandler),
    (r'/add_booking_extrainfo', AddBookingExtraInfoHandler),
    (r'/apply_promotion_code', ApplyPromotionCodeHandler),
    (r'/apply_promotion_code_upcoming', ApplyPromotionCodeToUpComingBookingHandler),
    (r'/update_booking', EditBookingHandler),
    (r'/update_available', EditAvailableHandler),
    (r'/notify_service', NotifyServiceAvailabilityHandler),
    (r'/cancel_charge', CancelChargeHandler),
    (r'/faq', FAQHandler),
    (r'/faq_master', FAQMasterHandler),
    (r'/register_card', RegisterCardHandler),
    (r'/modify_userinfo', ModifyUserInfoHandler),
    (r'/dummy', DummyHandler),
    (r'/request_available_schedules', RequestAvailableSchedulesHandler),
    (r'/request_available_update_schedules', RequestAvailableSchedulesForUpdateHandler),
    (r'/request_available_change_circle_schedules', RequestAvailableSchedulesForChangeCircleHandler),
    (r'/change_circle_handler', ChangeCircleHandler),
    (r'/select_schedule', RequestSelectScheduleHandler),
    (r'/select_schedule_web', RequestSelectScheduleWebHandler),
    (r'/confirm_schedule', RequestConfirmScheduleHandler),
    (r'/confirm_schedule_for_manager', RequestConfirmScheduleForManagerHandler),
    (r'/confirm_schedule_adminweb', RequestConfirmScheduleAdminWebHandler),
    (r'/price_change',PriceHandler),
    (r'/pstatus_change',PaymentStatusHandler),
    (r'/cstatus_change',CleaningStatusHandler),
    (r'/update_additional_task', UpdateAdditionalTaskHandler),
    (r'/update_schedule', UpdateScheduleHandler),
    (r'/update_time', UpdateScheduleHandler2),
    (r'/remove_address', RemoveAddressHandler),
    (r'/reset_pwd', ResetPwdHandler),
    (r'/cards', UserCardHandler),
    (r'/set_default_card', SetDefaultCardHandler),
    (r'/apply_coupon_upcoming', ApplyCouponHandler),
    (r'/apply_cancel_coupon_upcoming', ApplyCancelCouponHandler),
    (r'/charge_history', UserPaymentChargeHistoryHandler),
    (r'/user_logs', UserEventLogHandler, dict(mongo=mongo)),
    (r'/test_proc', TestProcessHandler),
    (r'/user_address_info', UserAddressInfoHandler),

    (r'/confirm_schedule_new', RequestConfirmScheduleNewHandler),
    (r'/booking_charge', BookingChargeHandler),

    (r'/delete_user', DeleteUserHandler),
    (r'/delay_schedule', Delay30Handler),
    (r'/modify_booking_address', ModifyAddressBookingHandler),
    (r'/all_user_addresses', UserAllAddressHandler),
    (r'/user_payment_history', UserPaymentHistoryHandler),
    (r'/modify_additional_task', ModifyAdditionalTaskHandler),
    (r'/request_user_coupons', RequestUserCouponHandler),
    (r'/apply_user_coupon', ApplyUserCouponHandler),
    (r'/register_web', RegisterWebHandler),
    (r'/login_web', LoginWebHandler),
    (r'/request_time_price_web', RequestTimePriceWebHandler),
    (r'/request_available_schedules_web', RequestAvailableSchedulesWebHandler),
    (r'/confirm_schedule_web', RequestConfirmScheduleWebHandler),
    (r'/request_all_time_price', RequestAllTimePriceHandler),

    # moving clean
    (r'/request_mc_charge', RequestChargeHandler),

    # 11 st
    (r'/request_schedule_11', RequestAvailableSchedules11stHandler),
    (r'/request_booking_11', RequestSelectSchedule11stHandler),

    (r'/cancel_booking_for_manager', CancelBookingForManagerHandler),
    (r'/cancel_all_booking_for_manager', CancelAllBookingForManagerHandler),
    (r'/update_booking_for_manager', EditBookingForManagerHandler),
    (r'/master_count_by_gender', MasterGenderByRegionHandler),

    (r'/master_login', MasterLoginHandler),
    (r'/master_schedule_ondate', MasterScheduleOnDateHandler),
    (r'/master_set_pw', MasterSetPasswordHandler),
    (r'/master_check_pw', MasterCheckPasswordHandler),
    (r'/master_weekly_salary_old', MasterSalaryHandler),
    (r'/master_weekly_period_salary', MasterSalaryPeriodHandler),
    (r'/all_master_weekly_salary', AllWeeklySalaryHandler),
    (r'/master_add_point', MasterPointAddHandler),
    (r'/master_point', MasterPointDescriptionHandler),
    (r'/master_all_point', MasterPointTotalHandler),
    (r'/master_point_detail', MasterPointDetailHandler),
    (r'/master_work_list', MasterWorkListHandler),
    (r'/master_rating_history', MasterRatingHistoryHandler),
    (r'/master_work_date', MasterWorkDateHandler),
    (r'/master_guide_route', MasterRoutingGuideHandler),
    (r'/master_memos', AllMasterMemoInfoHandler),
    (r'/master_reset_pwd', MasterResetPasswordHandler),
    (r'/master_post_memo', MasterPostMemoHandler),
    (r'/master_pushkey', MasterPushkeyHandler),
    (r'/master_claim', MasterClaimHandler),
    (r'/all_master_claim', MasterAllClaimHandler),
    (r'/master_weekly_salary', NewMasterSalaryHandler),
    (r'/master_weekly_detail_salary', MasterWeeklyDetailSalaryHandler),
    (r'/master_names', MasterNamesHandler),
    (r'/modify_alergy', MasterModifyAlergyStateHandler),
    (r'/master_remove', MasterRemoveHandler),
    (r'/all_master_name', AllMasterNameHandler),
    (r'/add_account', MasterAddAccountHandler),
    (r'/register_master', RegisterMasterHandler),
    (r'/request_master_names', GetMasterNamesHandler),
    (r'/monthly_salary', MasterMonthlySalaryHandler),
    (r'/all_monthly_salary', MasterAllMonthlySalaryHandler),
    (r'/send_hm_noti', NotifyHomemasterHandler),
    (r'/apply_homemaster', ApplyHomemasterHandler),
    (r'/master_change', MasterHandler),
    (r'/master_add_prize', MasterAddPrizeHandler),
    (r'/master_reset_prize', MasterResetPrizeHandler),
    (r'/master_prize', MasterPrizeHandler),
    (r'/master_penalty', MasterPenaltyHandler),
    (r'/master_charge_penalty', MasterChargePenaltyHandler),
    (r'/master_monthly_penalty', MasterPenaltyAccumulateHandler),
    (r'/extra_minute', ExtraMinutesHandler),
    (r'/homemaster_notices', MasterNoticeHandler),
    (r'/edit_notice', MasterNoticeEditHandler),
    (r'/remove_notice', MasterNoticeRemoveHandler),

    (r'/version', VersionHandler),
    (r'/revenue', WeeklyRevenueHandler),
    (r'/indicators', WeeklyIndicatorHandler),
    (r'/add_reject_relation', RejectRelationHandler),
    (r'/user_reject_relation', UserRejectRelationHandler),
    (r'/monthly_revenue', MonthlyRevenueHandler),

    (r'/request_moving_booking', MovingCleaningNotifyManagerHandler),

    (r'/tapi', TAPIHandler),
    (r'/request_time_price', RequestTimePriceHandler),

    # ################ admin_new ################
    (r'/users', SearchUserInfoHandler),
    (r'/claim_input', ClaimInputHandler),
    (r'/search_claims', ClaimSearchHandler),
    (r'/unpaid_list', UnpaidListHandler),
    (r'/modify_rate_handler', ModifyRateHandler),
    (r'/unassigned_bookings', UnassignedBookingsHandler),
    (r'/remove_unassigned_booking', RemoveUnassignedBookingsHandler),
    (r'/booking_change_history', BookingChangeHistoryHandler, dict(mongo=mongo)),
    (r'/request_modify', MasterBookingModifyRequestHandler),
    (r'/request_off', MasterDayoffRequestHandler),
    (r'/request_cancel_off', MasterDayoffCancelHandler),
    (r'/monthly_request_count', MasterMonthlyRequestCountHandler),
    (r'/send_notice_sms', NoticeSMSHandler),
    (r'/input_admin_memo', InputAdminMemoHandler),
    (r'/request_admin_memos', RequestAdminMemoHandler),
    (r'/check_bank_account', CheckBankAccountHandler),
    (r'/discount_booking', DiscountUpcomingCleaningHandler),
    (r'/cancel_payment', CancelPaymentHandler),
    (r'/search_master', SearchMasterInfoHandler),
    (r'/create_user_coupon', CreateUserCouponHandler),
    (r'/request_available_schedules_for_adminweb', RequestAvailableSchedulesForAdminWebHandler),
    (r'/request_select_schedules_for_adminweb', RequestSelectSchedulesForAdminWebHandler),
    (r'/input_master_notice', InputMasterNoticeHandler),
    (r'/request_master_notices', RequestMasterNoticesHandler),
    (r'/request_user_coupon_adminweb', RequestUserCouponAdminWebHandler),

    ############################# for admin #############################
    (r'/hm_all_userinfo', AllUserInfoHandler),
    (r'/hm_masterinfo', MasterInfoHandler),
    (r'/hm_all_masterinfo', AllMasterInfoHandler),
    (r'/hm_managerinfo', ManagerInfoHandler),
    (r'/hm_all_managerinfo', AllManagerInfoHandler),
    (r'/hm_schedule_ondate', MasterScheduleTimeOnDateInfoHandler),
    (r'/hm_booking_request', AutoRegisterBookingHandler),
    (r'/hm_add_master', MasterAddHandler),
    (r'/hm_delete_master', MasterDeleteHandler),
    (r'/hm_update_master_basic', MasterUpdateBasicHandler),
    (r'/hm_update_master_time', MasterUpdateTimeHandler),
    (r'/hm_update_master_area', MasterUpdateAreaHandler),
    (r'/hm_change_master', ChangeMasterOnScheduleHandler),
    (r'/hm_change_all_master', ChangeMasterOnAllScheduleHandler),
    (r'/hm_add_manager', ManagerAddHandler),
    (r'/hm_update_manager', ManagerUpdateHandler),
    (r'/hm_booking_info', BookingInfoHandler),
    (r'/hm_master_daily_salary', MasterSalaryOnDateHandler),
    (r'/hm_add_existing_booking', RegisterUserAndBookingHandler),
    (r'/hm_all_promotion_codes', ManagePromotionCodeHandler),
    (r'/hm_user_memo', MemoInfoHandler),
    (r'/hm_process_user_memo', ProcessUserMemoHandler),
    (r'/hm_all_unmatched', UnMatchedBookingHandler),
    (r'/hm_set_completed', ScheduleCompleteHandler),
    (r'/hm_set_completed_with_time', ScheduleCompleteWithTimeHandler),
    (r'/hm_set_started', ScheduleStartHandler),
    (r'/hm_set_started_with_time', ScheduleStartWithTimeHandler),
    (r'/hm_set_paid', SchedulePaidHandler),
    (r'/hm_payment_history', PaymentHistoryHandler),
    (r'/hm_manual_charge', ManualChargeHandler),
    (r'/hm_charge', ChargeHandler),
    (r'/hm_all_paid_bookings', AllPaidBookingInfoHandler),
    (r'/hm_all_bookings', AllBookingInfoHandler),
    (r'/hm_all_ratings', AllRatingInfoHandler),
    (r'/hm_master_avg_rating', MasterAvgRatingHandler),
    (r'/hm_master_notify_content', MasterNotificationContentHandler),
    (r'/hm_modify_entrance', ModifyEntranceMethodHandler),
    (r'/hm_modify_msg', ModifyMsgHandler),
    (r'/hm_master_gender', ModifyMasterGenderHandler),
    (r'/hm_stats', HomemasterStatInfoHandler),
    (r'/hm_user_search', UserSearchHandler),
    (r'/hm_chargeatonce', ManualUnpaidChargeHandler),
    (r'/hm_not_request_booking_user', UserNotRequestBookingHandler),
    (r'/hm_get_prediction_ab_group', UserGroupABHandler),
    (r'/hm_all_memos', AllMemoInfoHandler),
    (r'/policy', PolicyHandler),
    (r'/ios_none', IOSNoneCustomerHandler),
    (r'/user_registerinfo', UserRegisterInfoHandler),

    (r'/get_youtube_content', GetYouTubeContentHandler),
    (r'/modify_account_no', ModifyAccountNoHandler),

    (r'/inquery_office', InqueryOfficeCleaningHandler),

    (r'/rbusers', RegularBasisUserManageHandler),
    (r'/rb_update', UpdateRegularBasisUserHandler),

    (r'/check_unpaid_booking', CheckUnpaidBookingHandler),
    (r'/process_unpaid_booking', ProcessUnpaidBookingHandler),

    (r'/get_active_events', ActiveEventHandler),
    (r'/is_free_event_on', FreeOneTimeRegularCleaningHandler),

    (r'/submit_checklist', SubmitChecklistHandler, dict(mongo=mongo)),
    (r'/user_checklist', UserChecklistHandler, dict(mongo=mongo)),

    (r'/request_cleaning', RequestCleaningHandler, dict(mongo=mongo)),
    (r'/select_payment_method', SelectPaymentMethodHandler, dict(mongo=mongo)),
    (r'/register_and_charge', RegisterCardAndChargeHandler, dict(mongo=mongo)),
    (r'/web_cleaning', CleaningHandler, dict(mongo=mongo)),
    (r'/proc_web_cleaning', ProcessCleaningHandler, dict(mongo=mongo)),
    (r'/check_my_cleaning', CheckMyCleaningHandler, dict(mongo=mongo)),
    (r'/remove_web_cleaning', RemoveCleaningHandler, dict(mongo=mongo)),
    (r'/update_web_cleaning_status', UpdateWebCleaningStatusHandler, dict(mongo=mongo))

    ], autoreload=True)
