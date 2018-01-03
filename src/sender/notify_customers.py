#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')


import datetime as dt
import coolsms as sms
try:
    from utils.secrets import COOL_SMS_API_KEYS, COOL_SMS_API_SECRET, MAIN_CALL, MANAGERS_CALL
except ImportError:
    COOL_SMS_API_KEYS = ''
    COOL_SMS_API_SECRET = ''
    MAIN_CALL = ''
    MANAGERS_CALL = ''

from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, User
from data.encryption import aes_helper as aes
from sqlalchemy import and_, or_, func, not_
from data_analytic.mixpanel_client import Mixpanel
try:
    from utils.secrets import MX_KEY, MX_SECRET
except ImportError:
    MX_KEY = ''
    MX_SECRET = ''


class Message_Sender(object):
    def __init__(self):
        print COOL_SMS_API_SECRET, COOL_SMS_API_KEYS
        self.sender = sms.rest(COOL_SMS_API_KEYS, COOL_SMS_API_SECRET)

    def send(self, sender = MAIN_CALL, mtype = None, to = None, subject = None, text = None, image = None):
        result = self.sender.send(to = to, text = text, sender = sender, mtype = mtype, subject = subject)
        return result

def price_update_mms_practice():
    update_time = dt.datetime(2016, 9, 27)
    sms_sender = Message_Sender()
    text = '''안녕하세요. 홈마스터입니다. 홈마스터를 이용해주셔서 감사드립니다.
현재 이용 중인 정기고객 대상으로 홈마스터 서비스의 가격 인하 안내 드립니다.
9월 27일 부터 현재 고객님께서 이용중인 금액 대비 7,900원 ~ 5,900원 저렴하게 이용 가능 합니다.
변경된 가격은 등록된 카드로 자동결제 됩니다. 감사합니다.'''
    print sms_sender.send(sender = MAIN_CALL, mtype = 'lms', to = '01068015254,01034576360', subject=str('홈마스터에서 알려드립니다.'), text = str(text))

def send_survey_link():
    update_time = dt.datetime(2016, 9, 27)

    session = Session()
    result  = session.query(User) \
                     .filter(func.length(func.aes_decrypt(func.from_base64(User.phone), func.substring(User.salt, 1, 16))) < 12) \
                     .filter(User.phone != 'out') \
                     .filter(User.active == 1) \
                     .filter(not_(User.email.op('regexp')(r'._$'))) \
                     .all()

    sms_sender = Message_Sender()

    for row in result:
        key = row.salt[:16]
        crypto = aes.MyCrypto(key)

        name = crypto.decodeAES(row.name)
        phone = crypto.decodeAES(row.phone)
        print name, phone

        text = '''(광고) 홈마스터 설문조사참여하고 신세계 상품권 받으세요^^
https://goo.gl/kYNti3
~12.31'''
        print sms_sender.send(sender = MAIN_CALL, mtype = 'lms', to = str(phone), text = str(text))

if __name__ == '__main__':
    send_survey_link()
