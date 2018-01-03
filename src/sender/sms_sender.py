#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import coolsms as sms
import datetime as dt
import rest.booking.booking_constant as BC
from sqlalchemy import and_, or_
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, Master, User, UserAddress, UserDefaultAddress
from data.encryption import aes_helper as aes
from data.dao.userdao import UserDAO
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from utils.datetime_utils import timedelta_to_time, convert_datetime_format, convert_datetime_format2
from logger.mongo_logger import get_mongo_logger
try:
    from utils.secrets import COOL_SMS_API_KEYS, COOL_SMS_API_SECRET, MAIN_CALL, MANAGERS_CALL
except ImportError:
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

    def send(self, sender = MAIN_CALL, mtype = None, to = None, subject = None, text = None):
        #self.sender.set_type('lms')
        #result = self.sender.send(to = to, text = text, sender = sender, mtype = mtype, subject = subject, app_version = 'homemaster')
        #mongo_logger = get_mongo_logger()
        #mongo_logger.debug('sms notification was sent', extra = result)
        #return result
        return True

    def send_for_manager(self, sender = MAIN_CALL, mtype = None, to = None, subject = None, text = None, image = None):
        result = self.sender.send(to = to, text = text, sender = sender, mtype = mtype, subject = subject, image = image, app_version = 'homemaster')
        #mongo_logger = get_mongo_logger()
        #mongo_logger.debug('sms notification was sent to manager', extra = result)
        return result

    def send2(self, sender = MAIN_CALL, mtype = None, to = None, subject = None, text = None, image = None):
        result = self.sender.send(to = to, text = text, sender = sender, mtype = mtype, subject = subject, image = image, app_version = 'homemaster')
        #mongo_logger = get_mongo_logger()
        #mongo_logger.debug('sms notification was sent to manager', extra = result)
        return result


def send_promotion_code(user_phone, promotion_code):
    print user_phone, promotion_code
    sms_sender = SMS_Sender()
    user_phone = str(user_phone)
    text = UNAVAILABLE_USERS % str(promotion_code)
    print sms_sender.send_for_manager(sender = MAIN_CALL, mtype = 'lms', to = user_phone, subject = NOTIFY_TEXT_SUBJECT, text = text)


def send_booking_info_mms(booking_id):   
    try:
        session = Session()

        try:
            row = session.query(Booking, User) \
                         .join(User, Booking.user_id == User.id) \
                         .filter(Booking.id == booking_id) \
                         .filter(Booking.cleaning_status == BC.BOOKING_UPCOMMING) \
                         .one()

        except NoResultFound, e:
                session.close()
                return False               

        except MultipleResultsFound, e:
            session.close()
            return False

        userdao = UserDAO()
        key = userdao.get_user_salt_by_id(row.User.id)[:16]
        crypto = aes.MyCrypto(key)

        user_name = str(crypto.decodeAES(row.User.name))
        user_phone = str(crypto.decodeAES(row.User.phone))

        text = '%s 고객님 감사드립니다 :)\n홈마스터 서비스에 대한 안내는 첨부된 이미지를 참고 부탁드립니다~' % user_name

        sms_sender = SMS_Sender()
        sms_sender.send_for_manager(sender = MAIN_CALL, mtype = 'mms', to = user_phone, subject = NOTIFY_TEXT_SUBJECT, text = str(text), image='/home/dev/customer_mms.png')

    except Exception, e:
        print_err_detail(e)
    finally:
        session.close()
        return True


def send_booking_iphone(booking_id):
    try:
        session = Session()

        try:
            row = session.query(Booking, Master, User) \
                         .join(Master, Booking.master_id == Master.id) \
                         .join(User, Booking.user_id == User.id) \
                         .filter(Booking.id == booking_id) \
                         .filter(Booking.cleaning_status == BC.BOOKING_UPCOMMING) \
                         .one()

        except NoResultFound, e:
                session.close()
                return False               

        except MultipleResultsFound, e:
            session.close()
            return False

        if row.User.devicetype == 'android':
            return False

        userdao = UserDAO()
        key = userdao.get_user_salt_by_id(row.User.id)[:16]
        crypto = aes.MyCrypto(key)

        user_name = str(crypto.decodeAES(row.User.name))
        user_phone = str(crypto.decodeAES(row.User.phone))

        date_str = str(convert_datetime_format2(row.Booking.start_time))
        price = str(row.Booking.price_with_task)

        print user_name, user_phone, date_str, price
        print BOOKING_FOR_IPHONE

        sms_sender = SMS_Sender()
        text = BOOKING_FOR_IPHONE % (user_name, date_str, price)
        sms_sender.send_for_manager(sender = MAIN_CALL, mtype = 'mms', to = user_phone, subject = NOTIFY_TEXT_SUBJECT, text = str(text), image='/home/dev/customer_mms.png')

    except Exception, e:
        print_err_detail(e)
    finally:
        session.close()
        return True


def additional_task_string(additional_task):
    tasks = ['청소기 없음', '양문형 냉장고', '일문형 냉장고', '옷장정리', '빨래', '배란다', '창문,창틀']
    bits = "{0:07b}".format(additional_task)

    master_tasks = []

    for i in xrange(7):
        if bits[i] == '1':
            master_tasks.append(tasks[i])

    return ','.join(master_tasks)


def send_booking_requested(booking_id):
    try:
        session = Session()

        try:
            row = session.query(Booking, Master, User) \
                         .join(Master, Booking.master_id == Master.id) \
                         .join(User, Booking.user_id == User.id) \
                         .filter(Booking.id == booking_id) \
                         .filter( Booking.cleaning_status == BC.BOOKING_UPCOMMING) \
                         .one()

        except NoResultFound, e:
                session.close()
                return False               

        except MultipleResultsFound, e:
            session.close()
            return False

        userdao = UserDAO()
        key = userdao.get_user_salt_by_id(row.User.id)[:16]
        crypto = aes.MyCrypto(key)

        user_name           = str(crypto.decodeAES(row.User.name))
        appointment_type    = row.Booking.appointment_type

        app_type = ''
        if appointment_type == 0 or appointment_type == 3:
            app_type = '1회'
        elif appointment_type == 1:
            app_type = '4주 1회'
        elif appointment_type == 2:
            app_type = '2주 1회'
        elif appointment_type == 4:
            app_type = '매주'

        sms_sender = SMS_Sender()
        text = '%s고객님, 예약됨 (%s)' % (user_name, app_type)
        sms_sender.send_for_manager(sender = MAIN_CALL, mtype = 'sms', to = MANAGERS_CALL, subject = None, text = text)

    except Exception, e:
        print_err_detail(e)
    finally:
        session.close()
        return True


def send_memo_requested(user_id):
    try:
        session = Session()

        try:
            row = session.query(User) \
                         .filter(User.id == user_id) \
                         .one()

        except NoResultFound, e:
                session.close()
                return False               

        except MultipleResultsFound, e:
            session.close()
            return False

        userdao = UserDAO()
        key = userdao.get_user_salt_by_id(user_id)[:16]
        crypto = aes.MyCrypto(key)

        user_name           = str(crypto.decodeAES(row.name))

        sms_sender = SMS_Sender()
        text = '%s고객님, 문의 요청됨' % user_name
        sms_sender.send_for_manager(sender = MAIN_CALL, mtype = 'sms', to = MANAGERS_CALL, subject = None, text = text)

    except Exception, e:
        print_err_detail(e)
    finally:
        session.close()
        return True


def send_rating_granted(booking_id, c_rate, m_rate):
    try:
        session = Session()

        try:
            row = session.query(Booking, Master, User) \
                         .join(Master, Booking.master_id == Master.id) \
                         .join(User, Booking.user_id == User.id) \
                         .filter(Booking.id == booking_id) \
                         .one()

        except NoResultFound, e:
                session.close()
                print e
                return False               

        except MultipleResultsFound, e:
            session.close()
            print e
            return False

        userdao = UserDAO()
        key = userdao.get_user_salt_by_id(row.User.id)[:16]
        crypto = aes.MyCrypto(key)

        user_name           = str(crypto.decodeAES(row.User.name))
        master_name         = row.Master.name

        sms_sender = SMS_Sender()
        text = '%s고객님, %s마스터님에게 평가완료 (%.1f, %.1f)' % (user_name, master_name, c_rate, m_rate)
        sms_sender.send_for_manager(sender = MAIN_CALL, mtype = 'sms', to = MANAGERS_CALL, subject = None, text = text)

    except Exception, e:
        print_err_detail(e)
    finally:
        session.close()
        return True



def send_24hours_ahead_reminder(master_phone, master_name, no_jobs):
    sms_sender = SMS_Sender()
    text = BOOKING_MASTER_HOUR % (master_name, no_jobs)
    print sms_sender.send(sender = MAIN_CALL, mtype = 'lms', to = master_phone, subject = BOOKING_TEXT_SUBJECT, text = text)


def send_confirm_text(booking_id):
    try:
        session = Session()

        try:
            row = session.query(Booking, Master, User, UserAddress) \
                         .join(Master, Booking.master_id == Master.id) \
                         .join(User, Booking.user_id == User.id) \
                         .join(UserDefaultAddress, User.id == UserDefaultAddress.user_id) \
                         .join(UserAddress, and_(UserAddress.user_id == UserDefaultAddress.user_id, UserAddress.user_addr_index == UserDefaultAddress.address_idx)) \
                         .filter(Booking.id == booking_id) \
                         .filter(Booking.cleaning_status == BC.BOOKING_UPCOMMING) \
                         .one()

        except NoResultFound, e:
                session.close()
                return False               

        except MultipleResultsFound, e:
            session.close()
            return False

        userdao = UserDAO()
        key = userdao.get_user_salt_by_id(row.User.id)[:16]
        crypto = aes.MyCrypto(key)

        master_phone        = str(row.Master.phone)
        master_name         = str(row.Master.name)
        user_name           = str(crypto.decodeAES(row.User.name))
        date                = str(convert_datetime_format(row.Booking.start_time))
        address             = str(crypto.decodeAES(row.UserAddress.address))
        appointment_type    = str(4 / row.Booking.appointment_type) + '주' \
                              if row.Booking.appointment_type != BC.ONE_TIME \
                              and row.Booking.appointment_type != BC.ONE_TIME_BUT_CONSIDERING \
                              else '1회'
        additional_task     = str(additional_task_string(row.Booking.additional_task))
        take_time           = timedelta_to_time(row.Booking.estimated_end_time - row.Booking.start_time)
        take_time_str       = '%d시간 %d분' % (take_time.hour, take_time.minute)
        message             = str(row.Booking.message)
        trash_location      = str(row.Booking.trash_location)

        # notify homemaster about appointment
        sms_sender = SMS_Sender()
        text = BOOKING_CONFIRM_TEXT % (master_name, user_name, date, address, appointment_type, additional_task, take_time_str, message, trash_location)
        sms_sender.send(sender = MAIN_CALL, mtype = 'lms', to = master_phone, subject = BOOKING_TEXT_SUBJECT, text = text)

    except Exception, e:
        print_err_detail(e)
    finally:
        session.close()
        return True


def send_updated_text(booking_id, org_date):
    try:
        session = Session()

        try:
            row = session.query(Booking, Master, User, UserAddress) \
                         .join(Master, Booking.master_id == Master.id) \
                         .join(User, Booking.user_id == User.id) \
                         .join(UserDefaultAddress, User.id == UserDefaultAddress.user_id) \
                         .join(UserAddress, and_(UserAddress.user_id == UserDefaultAddress.user_id, UserAddress.user_addr_index == UserDefaultAddress.address_idx)) \
                         .filter(Booking.id == booking_id) \
                         .filter(Booking.cleaning_status == BC.BOOKING_UPCOMMING) \
                         .one()

        except NoResultFound, e:
                session.close()
                return False               

        except MultipleResultsFound, e:
            session.close()
            return False

        userdao = UserDAO()
        key = userdao.get_user_salt_by_id(row.User.id)[:16]
        crypto = aes.MyCrypto(key)

        master_phone        = str(row.Master.phone)
        master_name         = str(row.Master.name)
        user_name           = str(crypto.decodeAES(row.User.name))
        date                = str(convert_datetime_format(row.Booking.start_time))
        address             = str(crypto.decodeAES(row.UserAddress.address))
        appointment_type    = str(4 / row.Booking.appointment_type) + '주' \
                              if row.Booking.appointment_type != BC.ONE_TIME \
                              and row.Booking.appointment_type != BC.ONE_TIME_BUT_CONSIDERING \
                              else '1회'
        additional_task     = str(additional_task_string(row.Booking.additional_task))
        take_time           = timedelta_to_time(row.Booking.estimated_end_time - row.Booking.start_time)
        take_time_str       = '%d시간 %d분' % (take_time.hour, take_time.minute)
        message             = str(row.Booking.message)
        trash_location      = str(row.Booking.trash_location)

        # notify homemaster about appointment
        sms_sender = SMS_Sender()
        text = BOOKING_UPDATE_TEXT % (master_name, user_name, org_date, user_name, date, address, appointment_type, additional_task, take_time_str, message, trash_location)
        sms_sender.send(sender = MAIN_CALL, mtype = 'lms', to = master_phone, subject = BOOKING_TEXT_SUBJECT, text = text)

    except Exception, e:
        print_err_detail(e)
    finally:
        session.close()
        return True


if __name__ == '__main__':
    send_booking_info_mms('PZelBeRGpvGd90Lj')
    #print additional_task_string(11)
    #send_24hours_ahead_reminder('01034576360', '변영표', '3')
    #send_promotion_code('01034576360', 'dafgagaertafafda')
    

