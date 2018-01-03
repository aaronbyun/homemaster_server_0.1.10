#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import coolsms as sms

try:
    from utils.secrets import SMS_ON, COOL_SMS_API_KEYS, COOL_SMS_API_SECRET, MAIN_CALL, MANAGERS_CALL
except ImportError:
    SMS_ON = True
    COOL_SMS_API_KEYS = ''
    COOL_SMS_API_SECRET = ''
    MAIN_CALL = ''
    MANAGERS_CALL = ''

try:
    from utils.stipulation_text import BOOKING_TYPE_DICT, BOOKING_CONFIRM_TEXT, BOOKING_UPDATE_TEXT, BOOKING_TEXT_SUBJECT, BOOKING_MASTER_HOUR, UNAVAILABLE_USERS, NOTIFY_TEXT_SUBJECT, BOOKING_FOR_IPHONE
except ImportError:
    BOOKING_TYPE_DICT = {}
    BOOKING_CONFIRM_TEXT = ''
    BOOKING_UPDATE_TEXT = ''
    BOOKING_TEXT_SUBJECT = ''
    BOOKING_MASTER_HOUR = ''
    UNAVAILABLE_USERS = ''
    NOTIFY_TEXT_SUBJECT = ''
    BOOKING_FOR_IPHONE = ''

class SMS_Sender(object):
    def __init__(self):
        self.sender = sms.rest(COOL_SMS_API_KEYS, COOL_SMS_API_SECRET)
        self.sender.set_type('lms')
        print self.sender.get_type()

    def send(self, sender = MAIN_CALL, mtype = None, to = None, subject = '[홈마스터 알림]', text = None, image = None):
        result = self.sender.send(to = to, text = text, sender = sender, mtype = mtype, subject = subject, image = image, app_version = 'homemaster')
        return result

sender = SMS_Sender()

def send_lms_new_booking(master_phone, master_name, appointment_type, cleaning_time, address, have_pet):
    if not SMS_ON:
        return

    text = '''{} 홈마스터님, 새로운 예약이 잡혔습니다. 앱에서 일정을 확인해주세요.

주기 : {}
날짜 : {}
주소 : {}
애완동물 {}'''.format(master_name, appointment_type, cleaning_time, address, have_pet)

    sender.send(mtype = 'lms', to = master_phone, text = text)

def send_lms_cancel_booking(master_phone, master_name, user_name, cleaning_time, address, reason):
    if not SMS_ON:
        return

    text = '''{} 홈마스터님, 예약이 1회 취소 되었습니다. 앱에서 일정을 확인해주세요.

{} 고객님
날짜 : {}
주소 : {}
사유 : {}'''.format(master_name, user_name, cleaning_time, address, reason)

    sender.send(mtype = 'lms', to = master_phone, text = text)

def send_lms_cancel_all_booking(master_phone, master_name, user_name, address, reason):
    if not SMS_ON:
        return

    text = '''{} 홈마스터님, 정기고객 일정이 전체 취소 되었습니다. 앱에서 일정을 확인해주세요.

{} 고객님
주소 : {}
사유 : {}'''.format(master_name, user_name, address, reason)

    sender.send(mtype = 'lms', to = master_phone, text = text)


# 변경
def send_lms_change_booking_one_time_same_master(master_phone, master_name, user_name, org_date, new_date):
    if not SMS_ON:
        return

    text = '''{} 홈마스터님, {} 고객님 1회 일정이 변경 되었습니다. 앱에서 일정을 확인해주세요

기존일정 : {}
새 일정 : {}'''.format(master_name, user_name, org_date, new_date)
    sender.send(mtype = 'lms', to = master_phone, text = text)

def send_lms_changed_gone_one_time_org_master(master_phone, master_name, user_name, org_date):
    if not SMS_ON:
        return

    text = '''{} 홈마스터님, {} 고객님 1회 일정이 변경 되었습니다. 앱에서 일정을 확인해주세요

기존일정 : {}'''.format(master_name, user_name, org_date)
    sender.send(mtype = 'lms', to = master_phone, text = text)



def send_lms_changed_gone_weekly_one_same_master(master_phone, master_name, user_name, org_date, new_date):
    if not SMS_ON:
        return

    text = '''{} 홈마스터님, {} 고객님 정기 1회 일정이 변경 되었습니다. 앱에서 일정을 확인해주세요

기존일정 : {}
새 일정 : {}'''.format(master_name, user_name, org_date, new_date)
    sender.send(mtype = 'lms', to = master_phone, text = text)

def send_lms_changed_gone_weekly_one_org_master(master_phone, master_name, user_name, org_date):
    if not SMS_ON:
        return

    text = '''{} 홈마스터님, {} 고객님 정기 1회 일정이 변경 되었습니다. 앱에서 일정을 확인해주세요

기존일정 : {}'''.format(master_name, user_name, org_date)
    sender.send(mtype = 'lms', to = master_phone, text = text)

def send_lms_changed_gone_weekly_one_new_master(master_phone, master_name, user_name, cleaning_time, address, have_pet):
    if not SMS_ON:
        return

    text = '''{} 홈마스터님, {} 고객님 정기 1회 일정이 배정 되었습니다. 앱에서 일정을 확인해주세요

날짜 : {}
주소 : {}
애완동물 {}'''.format(master_name, user_name, cleaning_time, address, have_pet)
    sender.send(mtype = 'lms', to = master_phone, text = text)



def send_lms_changed_gone_weekly_all_same_master(master_phone, master_name, user_name, new_date):
    if not SMS_ON:
        return

    text = '''{} 홈마스터님, {} 고객님 전체 일정이 변경 되었습니다. 앱에서 일정을 확인해주세요

새 일정 : {}'''.format(master_name, user_name, new_date)
    sender.send(mtype = 'lms', to = master_phone, text = text)

def send_lms_changed_gone_weekly_all_org_master(master_phone, master_name, user_name, org_date):
    if not SMS_ON:
        return

    text = '''{} 홈마스터님, {} 고객님 전체 일정이 변경취소 되었습니다. 앱에서 일정을 확인해주세요

기존일정 : {}'''.format(master_name, user_name, org_date)
    sender.send(mtype = 'lms', to = master_phone, text = text)

def send_lms_changed_gone_weekly_all_new_master(master_phone, master_name, user_name, cleaning_time, address, have_pet):
    if not SMS_ON:
        return

    text = '''{} 홈마스터님, {} 고객님 전체 일정이 새로 배정 되었습니다. 앱에서 일정을 확인해주세요

날짜 : {}
주소 : {}
애완동물 {}'''.format(master_name, user_name, cleaning_time, address, have_pet, cleaning_time, address, have_pet)
    sender.send(mtype = 'lms', to = master_phone, text = text)


if __name__ == '__main__':
    send_lms_new_booking('01034576360,01071841064', '변영효', '2주1회', '2016년 12월 29일 오후 3시', \
                        '경기도 성남시 분당구 판교로 20 305-1702', '있음')

    send_lms_cancel_booking('01034576360,01071841064', '변영효', '나고객', '2016년 12월 29일 오후 3시', \
                            '경기도 성남시 분당구 판교로 20 305-1702', '이번에 여행을 가요')
    send_lms_cancel_all_booking('01034576360,01071841064', '변영효', '나고객', \
                            '경기도 성남시 분당구 판교로 20 305-1702', '다른 홈마스터')


    send_lms_change_booking_one_time_same_master('01034576360', '변영효', '나고객', '2016년 12월 29일 오후 3시', '2016년 12월 29일 오후 5시')

    master_phone = '01034576360'
    master_name = '변영효'
    user_name = '나고객'
    appointment_type = '2주1회'
    cleaning_time = '2016년 12월 29일 오후 3시'
    org_date = '2016년 12월 29일 오후 3시'
    new_date = '2016년 12월 31일 오후 5시'
    address = '경기도 성남시 분당구 판교로 20 305-1702'
    reason = '이사가요'
    have_pet = '없음'

    send_lms_changed_gone_one_time_org_master(master_phone, master_name, user_name, org_date)
    send_lms_changed_gone_weekly_one_same_master(master_phone, master_name, user_name, org_date, new_date)
    send_lms_changed_gone_weekly_one_org_master(master_phone, master_name, user_name, org_date)
    send_lms_changed_gone_weekly_one_new_master(master_phone, master_name, user_name, cleaning_time, address, have_pet)
    send_lms_changed_gone_weekly_all_same_master(master_phone, master_name, user_name, new_date)
    send_lms_changed_gone_weekly_all_org_master(master_phone, master_name, user_name, org_date)
    send_lms_changed_gone_weekly_all_new_master(master_phone, master_name, user_name, cleaning_time, address, have_pet)
