#-*- coding: utf-8 -*-

import sys

reload(sys)
sys.setdefaultencoding('utf-8')

import sys, os
import datetime


err_dict = {
    'err_mongodb'            : {'err_code' : '4000', 'err_msg' : 'mongodb error'},
    'err_mysql'              : {'err_code' : '4001', 'err_msg' : 'api error'},
    'err_login_no_match'     : {'err_code' : '4002', 'err_msg' : '아이디와 비밀번호가 일치하지 않습니다.'},
    'invalid_param'          : {'err_code' : '4003', 'err_msg' : '올바른 파라미터가 아닙니다.'},
    'err_salt_no_match'      : {'err_code' : '4004', 'err_msg' : '사용자 정보가 올바르지 않습니다.'},
    'err_dup_email'          : {'err_code' : '4005', 'err_msg' : '이미 등록된 이메일 입니다.'},
    'err_dup_phone'          : {'err_code' : '3999', 'err_msg' : '이미 등록된 번호 입니다.'},
    'err_dup_phone2'         : {'err_code' : '3998', 'err_msg' : '중복된 번호로 로그인에 실패하였습니다. 이메일로 로그인 해주세요.'},
    'err_payment'            : {'err_code' : '4006', 'err_msg' : 'credit card error'},
    'err_no_entry_to_cancel' : {'err_code' : '4007', 'err_msg' : 'no booking to cancel'},
    'err_no_entry_to_update' : {'err_code' : '4008', 'err_msg' : 'no booking to update'},
    'err_no_master'          : {'err_code' : '4009', 'err_msg' : 'no homemaster information'},
    'err_no_user_addr'       : {'err_code' : '4009', 'err_msg' : 'no user address'},
    'err_no_hm_in_that_area' : {'err_code' : '4010', 'err_msg' : 'no homemaster in that area'},
    'err_no_hm_at_that_time' : {'err_code' : '4011', 'err_msg' : 'no homemaster in that time'},
    'err_hm_update_time'     : {'err_code' : '4012', 'err_msg' : 'error occur when updating master available time'},
    'err_hm_update_area'     : {'err_code' : '4013', 'err_msg' : 'error occur when updating master available area'},
    'err_hm_assign_collision': {'err_code' : '4014', 'err_msg' : 'schedule collision detected'},
    'err_no_record'          : {'err_code' : '4015', 'err_msg' : 'no record found, it should return only one row'},
    'err_multiple_record'    : {'err_code' : '4016', 'err_msg' : 'multiple record found, it should return only one row'},
    'err_booking_timeout'    : {'err_code' : '4017', 'err_msg' : 'booking data was expired due to 5 minutes timeout'},
    'err_booking_payment'    : {'err_code' : '4018', 'err_msg' : 'booking payment was not successfully made, booking is not completed'},
    'err_no_used_promotion'  : {'err_code' : '4019', 'err_msg' : 'promotion code was already used'},
    'err_hm_have_next_schedule'  : {'err_code' : '4020', 'err_msg' : 'The homemaster have next appointment.'},
    'err_hm_no_recommendation'  : {'err_code' : '4021', 'err_msg' : 'No schedule to recommed'},
    'err_schedules_on_dates'  : {'err_code' : '4022', 'err_msg' : 'User already have schedules on one of the days'},
    'err_no_promotion_codes'  : {'err_code' : '4023', 'err_msg' : 'There are no promotion codes which are unused'},
    'err_login_no_record'     : {'err_code' : '4024', 'err_msg' : 'id is not on our service'},
    'err_code_already_issued'     : {'err_code' : '4025', 'err_msg' : 'The use alreay got issued promotion code'},
    'err_searching_address'     : {'err_code' : '4026', 'err_msg' : 'Address was not found'},
    'err_update_not_allowed'     : {'err_code' : '4027', 'err_msg' : 'Appointment canbe updated in 24 hours ahead'},
    'err_cancel_payment'     : {'err_code' : '4028', 'err_msg' : 'cancel failed'},
    'err_promotion_code_occupied'     : {'err_code' : '4029', 'err_msg' : 'promition code was alreay occupied'},
    'err_promotion_code_expire'     : {'err_code' : '4030', 'err_msg' : '할인코드 사용기간이 만료되었습니다.'},
    'err_promotion_code_zero'     : {'err_code' : '4031', 'err_msg' : '할인코드가 전부 사용되었습니다.'},
    'err_homemaster_occupied'     : {'err_code' : '4032', 'err_msg' : '다른 고객님이 해당 시간에 예약 중 입니다.'},
    'err_not_available'     : {'err_code' : '4033', 'err_msg' : '예약 가능한 날짜가 없습니다.'},
    'err_time_too_long'     : {'err_code' : '4034', 'err_msg' : '클리닝 1회당 가능 시간은 최대 12시간입니다. 이전 화면으로 돌아가 소요 시간을 12시간 이하로 줄여주세요.'},
    'err_id_not_found'    : {'err_code' : '4036','err_msg': 'There is no available master'},
    # 40366부터 진행
    'err_not_valid_master' : {'err_code' : '5001', 'err_msg' : '유효한 홈마스터 id(아이디)가 아닙니다.'},
    'err_user_id_unmatch' : {'err_code' : '5002', 'err_msg' : '해당 사용자의 유효한 쿠폰이 아닙니다.'},
    'err_coupon_already_applied' : {'err_code' : '5003', 'err_msg' : '해당 예약은 이미 쿠폰이 적용 되었습니다.'},
    'err_already_paid' : {'err_code' : '5004', 'err_msg' : '이미 결제 된 예약은 쿠폰 적용이 되지 않습니다.'},
    'err_no_coupon' : {'err_code' : '5005', 'err_msg' : '존재하지 않는 쿠폰입니다.'},
    'err_no_booking' : {'err_code' : '5006', 'err_msg' : '존재하지 않는 예약입니다.'},
    'err_no_booking_id_checklist' : {'err_code' : '5007', 'err_msg' : '잘못된 형식의 checklist 입니다.'},
    'err_no_zero_point' : {'err_code' : '5008', 'err_msg' : '초기화할 포인트가 없습니다.'},
    'err_no_cleaning_id' : {'err_code' : '5009', 'err_msg' : '클리닝 요청을 찾을 수 없습니다.'},
    'err_no_user_id' : {'err_code' : '5010', 'err_msg' : '사용자 아이디 오류'},
    'err_invalid_amount' : {'err_code' : '5009', 'err_msg' : '결제 금액 오류'},
    'err_web_no_matching_phone_pwd' : {'err_code' : '5010', 'err_msg' : '예약내역이 확인되지 않습니다.'},
    'err_charge_fail' : {'err_code' : '5011', 'err_msg' : '결제실패'}
            }

def print_err_detail(e):
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    print '-' * 100
    print datetime.datetime.now()
    print '### err -', exc_type, fname, exc_tb.tb_lineno, '###'
    print '### msg - ', e, '###'
    print '-' * 100
