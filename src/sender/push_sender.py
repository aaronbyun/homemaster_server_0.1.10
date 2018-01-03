#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

from err.error_handler import print_err_detail
from gcm import *
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel
from sqlalchemy import func
from data.session.mysql_session import engine, Session
from data.model.data_model import Master, MasterPushKey, MasterTimeSlot
from sms_sender import SMS_Sender

try:
    from utils.secrets import GCM_SERVER_API_KEY, MAIN_CALL
except ImportError:
    GCM_SERVER_API_KEY = 'AIzaSyDbXjIGX5ZRAi_rGjC6UXYqHr7Z0zqGb9E'
    MAIN_CALL = ''


try:
    from utils.stipulation_text import CLEANING_COMPLETE, BOOKING_USER_ONEHOUR, BOOKING_USER_TENMIN, CLEANING_COMPLETE, ESTIMATE_MASTER, NOTIFY_TEXT_SUBJECT, BOOKING_USER_ONEHOUR_IPHONE, BOOKING_USER_DAY_AHEAD, BOOKING_RATED, BOOKING_NEW, BOOKING_SCHEDULE_UPDATED,BOOKING_TASK_UPDATED, BOOKING_MSG_UPDATED, BOOKING_CANCELED,BOOKING_ALL_CANCELED, BOOKING_MASTER_HOUR

except ImportError:
    BOOKING_USER_ONEHOUR = ''
    BOOKING_USER_TENMIN = ''
    CLEANING_COMPLETE = ''
    ESTIMATE_MASTER = ''
    CLEANING_COMPLETE = ''
    NOTIFY_TEXT_SUBJECT = ''
    BOOKING_USER_ONEHOUR_IPHONE = ''
    BOOKING_USER_DAY_AHEAD = ''
    BOOKING_NEW = ''
    BOOKING_RATED = ''
    BOOKING_SCHEDULE_UPDATED = ''
    BOOKING_TASK_UPDATED = ''
    BOOKING_MSG_UPDATED = ''
    BOOKING_CANCELED = ''
    BOOKING_ALL_CANCELED = ''
    BOOKING_MASTER_HOUR = ''

class Push_Sender(object):
    def __init(self):
        pass

    def send(self, reg_ids, push_data):
        pass


class Android_Push_Sender(Push_Sender):
    def __init__(self):
        self.gcm  = GCM(GCM_SERVER_API_KEY)

    def send(self, reg_ids, push_data):
        mongo_logger = get_mongo_logger()
        try:
            self.gcm.json_request(registration_ids = reg_ids, data = push_data)
            mongo_logger.debug('push notification was sent', extra = push_data)
            return True
        except Exception, e:
            print_err_detail(e)
            mongo_logger.error('push notification was failed to send', extra = {'err' : str(e)})
            return False

class Ios_Push_Sender(Push_Sender):
    def __init__(self):
        pass

    def send(self, reg_ids, push_data):
        try:
            sms_sender = SMS_Sender()
            text = push_data['content']
            #result = sms_sender.send_for_manager(sender = MAIN_CALL, mtype = 'lms', to = str(reg_ids[0]), subject = NOTIFY_TEXT_SUBJECT, text = str(text))
            #if result['result_message'] == 'Success':
            #    return True
            #else:
            #    return False
        except Exception, e:
            print_err_detail(e)
            return False


class Normal_Push_Sender(Push_Sender):
    def __init__(self):
        pass

    def send(self, reg_ids, push_data):
        try:
            sms_sender = SMS_Sender()
            text = push_data['content']
            #result = sms_sender.send_for_manager(sender = MAIN_CALL, mtype = 'lms', to = str(reg_ids[0]), subject = NOTIFY_TEXT_SUBJECT, text = str(text))
            #if result['result_message'] == 'Success':
            #    return True
            #else:
            #    return False
        except Exception, e:
            print_err_detail(e)
            return False


class SenderFactory(object):
    def __init__(self):
        pass

    def create_sender(self, devicetype):
        if devicetype == 'android':
            sender = Android_Push_Sender()
        elif devicetype == 'ios':
            sender = Ios_Push_Sender()
        else:
            sender = Normal_Push_Sender()

        return sender


sender_factory = SenderFactory()


# ------------------------------------------------------------------------------------------------------------
# master push

# homemaster notification
def send_homemaster_notification(reg_ids, title, content):
    sender = sender_factory.create_sender("android") # 모든 홈마스터는 안드로이드
    data = {'title' : title, 'content' : content, 'command' : 'notify_homemaster'}
    return sender.send(reg_ids, data)


# notify all
def notify_all_active_homemaster(title = '알려드립니다.', content = '홈마스터님 공지사항을 확인해주세요^^'):
    ret = True

    session = Session()
    result = session.query(Master, MasterTimeSlot, MasterPushKey) \
                    .join(MasterTimeSlot, Master.id == MasterTimeSlot.master_id) \
                    .join(MasterPushKey, Master.id == MasterPushKey.master_id) \
                    .filter(Master.active == 1) \
                    .all()

    # for test purpoese of server
    '''result = session.query(Master, MasterPushKey) \
                    .join(MasterPushKey, Master.id == MasterPushKey.master_id) \
                    .filter(Master.id == '336c6743-0601-4bcc-97f5-a2c23567a4dc') \
                    .all()'''

    for row in result:
        name = row.Master.name
        push_key = row.MasterPushKey.pushkey

        try:
            send_homemaster_notification([push_key], title, content)
        except Exception, e:
            print e
            ret = False
            continue

    return ret

# 2 hours before
def send_master_ahead_notification(devicetype, reg_ids, booking_id, master_name, date):
    sender = sender_factory.create_sender(devicetype)

    title = '클리닝 시작 2시간전 알림입니다.'
    text = '안녕하세요 {} 홈마스터님, 오늘 {}에 클리닝 일정이 있습니다. 앱에서 확인 부탁드립니다.^^ 감사합니다!'.format(master_name, date)

    data = {'data' : booking_id, 'title' : title, 'content' : text, 'command' : 'notify_new_booking'}

    if sender.send(reg_ids, data):
        print 'push new booking sent successfully', devicetype
    else:
        print 'push new booking failed', devicetype


# 30 mins before
def send_master_before_complete_notification(devicetype, reg_ids, booking_id, master_name):
    sender = sender_factory.create_sender(devicetype)

    title = '클리닝 종료 30분전 알림입니다.'.format(master_name)
    text = '안녕하세요 {} 홈마스터님, 클리닝 종료시간이 30분 남았습니다. 마무리 부탁 드려요.^^ 혹시 시간이 더 필요하시면 고객센터로 연락 부탁드립니다. 감사합니다.^^'.format(master_name)

    data = {'data' : booking_id, 'title' : title, 'content' : text, 'command' : 'notify_new_booking'}

    if sender.send(reg_ids, data):
        print 'push new booking sent successfully', devicetype
    else:
        print 'push new booking failed', devicetype


# new booking
def send_new_booking_notification(devicetype, reg_ids, booking_id, date):
    sender = sender_factory.create_sender(devicetype)

    text = BOOKING_NEW % date
    data = {'data' : booking_id, 'title' : '새 예약 알림', 'content' : text, 'command' : 'notify_new_booking'}

    if sender.send(reg_ids, data):
        print 'push new booking sent successfully', devicetype
    else:
        print 'push new booking failed', devicetype

# one booking canceled
def send_booking_canceled(devicetype, reg_ids, booking_id, date, user_name):
    sender = sender_factory.create_sender(devicetype)

    text = BOOKING_CANCELED % (user_name, date)
    data = {'data' : booking_id, 'title' : '예약 취소 알림', 'content' : text, 'command' : 'notify_cancel_booking'}

    if sender.send(reg_ids, data):
        print 'push cancel booking sent successfully', devicetype
    else:
        print 'push cancel booking failed', devicetype

# all booking canceled
def send_all_bookings_canceled(devicetype, reg_ids, booking_id, date, user_name):
    sender = sender_factory.create_sender(devicetype)

    text = BOOKING_ALL_CANCELED % (user_name, date)
    data = {'data' : booking_id, 'title' : '전체 취소 알림', 'content' : text, 'command' : 'notify_cancel_all_booking'}

    if sender.send(reg_ids, data):
        print 'push cancel all sent successfully', devicetype
    else:
        print 'push cancel all failed', devicetype

# update msg booking
def send_booking_msg_updated(devicetype, reg_ids, booking_id, date):
    sender = sender_factory.create_sender(devicetype)

    text = BOOKING_MSG_UPDATED % date
    data = {'data' : booking_id, 'title' : '남기는 말 변경 알림', 'content' : text, 'command' : 'notify_update_msg_booking'}

    if sender.send(reg_ids, data):
        print 'push update msg sent successfully', devicetype
    else:
        print 'push update msg failed', devicetype

# update additional task
def send_booking_task_updated(devicetype, reg_ids, booking_id, date):
    sender = sender_factory.create_sender(devicetype)

    text = BOOKING_TASK_UPDATED % date
    data = {'data' : booking_id, 'title' : '추가사항 변경 알림', 'content' : text, 'command' : 'notify_update_task_booking'}

    if sender.send(reg_ids, data):
        print 'push update task sent successfully', devicetype
    else:
        print 'push update task failed', devicetype

# update schedule
def send_booking_schedule_updated(devicetype, reg_ids, booking_id, date):
    sender = sender_factory.create_sender(devicetype)

    text = BOOKING_SCHEDULE_UPDATED % date
    data = {'data' : booking_id, 'title' : '예약 일정 변경 알림', 'content' : text, 'command' : 'notify_update_schedule_booking'}

    if sender.send(reg_ids, data):
        print 'push update schedule sent successfully', devicetype
    else:
        print 'push update schedule failed', devicetype


def send_tomorrow_schedule_notification(devicetype, reg_ids, master_name, cleaning_count):
    sender = sender_factory.create_sender(devicetype)

    text = BOOKING_MASTER_HOUR % (master_name, cleaning_count)
    data = {'data' : '', 'title' : '내일 일정 알림', 'content' : text, 'command' : 'notify_tomorrow_booking'}

    if sender.send(reg_ids, data):
        print 'push tomorrow schedule sent successfully', devicetype
    else:
        print 'push tomorrow schedule failed', devicetype


# rate
def send_rated(device_type, reg_ids, booking_id, date):
    sender = sender_factory.create_sender(devicetype)

    text = BOOKING_RATED % date
    data = {'data' : booking_id, 'title' : '평가 완료', 'content' : text, 'command' : 'notify_rate_booking'}

    if sender.send(reg_ids, data):
        print 'push rated sent successfully', devicetype
    else:
        print 'push rated failed', devicetype


# ------------------------------------------------------------------------------------------------------------
# client push

def send_survey_notification(reg_ids, content):
    sender = sender_factory.create_sender('android')
    data = {'data' : '', 'title' : '상담/방문 베타 서비스 출시!', 'content' : content, 'command' : 'notify_survey1'}
    sender.send(reg_ids, data)


def send_coupon_notification(reg_ids, title):
    sender = sender_factory.create_sender('android')
    data = {'data' : '', 'title' : '10,000원 할인 쿠폰이 도착했어요', 'content' : title, 'command' : 'notify_coupon'}
    sender.send(reg_ids, data)

def send_24hours_ahead_price_notification(devicetype, reg_ids, booking_id, user_name, master_name, price):
    sender = sender_factory.create_sender(devicetype)

    text = BOOKING_USER_ONEHOUR_IPHONE % (user_name, master_name, price)
    data = {'data' : booking_id, 'title' : '48시간 전 알림', 'content' : text, 'command' : 'notify_24hrs_user'}

    if sender.send(reg_ids, data):
        print 'push 48hours ahead sent successfully', devicetype
    else:
        print 'push 48hours ahead failed', devicetype

def send_24hours_ahead_notification(devicetype, reg_ids, booking_id, user_name, master_name):
    sender = sender_factory.create_sender(devicetype)

    text = BOOKING_USER_ONEHOUR % (user_name, master_name)
    data = {'data' : booking_id, 'title' : '48시간 전 알림', 'content' : text, 'command' : 'notify_24hrs_user'}

    if sender.send(reg_ids, data):
        print 'push 48hours ahead sent successfully', devicetype
    else:
        print 'push 48hours ahead failed', devicetype


def send_day_ahead_notification(devicetype, reg_ids, booking_id, user_name, time_str):
    sender = sender_factory.create_sender(devicetype)

    text = BOOKING_USER_DAY_AHEAD % (user_name, time_str)
    data = {'data' : booking_id, 'title' : '24시간 전 알림', 'content' : text, 'command' : 'notify_day_ahead_user'}

    if sender.send(reg_ids, data):
        print 'push 24hours ahead sent successfully', devicetype
    else:
        print 'push 24hours ahead failed', devicetype


def send_10mins_ahead_notification(devicetype, reg_ids, booking_id):
    sender = sender_factory.create_sender(devicetype)

    text = BOOKING_USER_TENMIN
    data = {'data' : booking_id, 'title' : '10분 전 알림', 'content' : text, 'command' : 'notify_10mins_user'}

    if sender.send(reg_ids, data):
        print 'push 10mins ahead sent successfully', devicetype
    else:
        print 'push 10mins ahead failed', devicetype


def send_cleaning_complete_notification(devicetype, reg_ids, booking_id):
    sender = sender_factory.create_sender(devicetype)

    text = CLEANING_COMPLETE
    data = {'data' : booking_id, 'title' : '클리닝 종료 알림', 'content' : text, 'command' : 'notify_complete_user'}

    if sender.send(reg_ids, data):
        print 'push clearning complete sent successfully', devicetype
    else:
        print 'push clearning complete failed', devicetype


def send_rating_notification(devicetype, reg_ids, booking_id, user_name):
    sender = sender_factory.create_sender(devicetype)

    text = ESTIMATE_MASTER % user_name
    data = {'data' : booking_id, 'title' : '고객 평점', 'content' : text, 'command' : 'notify_rating_user'}

    if sender.send(reg_ids, data):
        print 'push rating push sent successfully', devicetype
    else:
        print 'push rating push failed', devicetype


if __name__ == '__main__':
    send_new_booking_notification('android', ['APA91bGWdC9UX-AwV91sDBvKTkKxdT6x-0_By6FVHqFojYe-Nv7kTwLU3ccMZFuNhGzOR6Q7N2vzB6eJJYmLr2CUX7CtRVnkHRSlYFKqh2tUvHmI03s2JyVkQrGt7qYpW3uNaA8d0RMY'], '1234', '2016년 3월 20일 오후 09:00')
    #send_booking_canceled('android', ['APA91bGWdC9UX-AwV91sDBvKTkKxdT6x-0_By6FVHqFojYe-Nv7kTwLU3ccMZFuNhGzOR6Q7N2vzB6eJJYmLr2CUX7CtRVnkHRSlYFKqh2tUvHmI03s2JyVkQrGt7qYpW3uNaA8d0RMY'], '1234', '2016년 3월 20일 오후 09:00')
    #send_all_bookings_canceled('android', ['APA91bGWdC9UX-AwV91sDBvKTkKxdT6x-0_By6FVHqFojYe-Nv7kTwLU3ccMZFuNhGzOR6Q7N2vzB6eJJYmLr2CUX7CtRVnkHRSlYFKqh2tUvHmI03s2JyVkQrGt7qYpW3uNaA8d0RMY'], '1234', '2016년 3월 20일 오후 09:00')
    #send_booking_schedule_updated('android', ['APA91bGWdC9UX-AwV91sDBvKTkKxdT6x-0_By6FVHqFojYe-Nv7kTwLU3ccMZFuNhGzOR6Q7N2vzB6eJJYmLr2CUX7CtRVnkHRSlYFKqh2tUvHmI03s2JyVkQrGt7qYpW3uNaA8d0RMY'], '1234', '2016년 3월 20일 오후 09:00')
