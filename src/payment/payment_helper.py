#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import requests
import json
import datetime as dt
import rest.booking.booking_constant as BC
from rest.response import Response
from data.session.mysql_session import engine, Session
from data.model.data_model import UserPaymentRecord, UserChargeRecord, Booking, ManualPaymentRecord
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel

try:
    from utils.secrets import PAYMENT_HOST, PAYMENT_PORT
except ImportError:
    PAYMENT_HOST = 'localhost'
    PAYMENT_PORT = 8443



def request_payment(user_id, user_name, booking_id, price, appointment_type, status = 'PAID'):
    try:
        mongo_logger = get_mongo_logger()
        mix = get_mixpanel()

        request_url = '%s:%d/homemaster_payment/request_payment_new' % (PAYMENT_HOST, PAYMENT_PORT)
        params = {'id' : user_id, 'name' : user_name, 'price' : price, 'product_name' : appointment_type}

        print user_id, price, appointment_type
        print request_url

        response = requests.post(request_url, data = params)
        print response.text
        result = json.loads(response.text)

        if result['response'] == Response.SUCCESS:
            # upate request payment record
            tid = result['tid']
            authdate = result['authdate']

            session = Session()
            # done in java server
            # status 'PAID', 'CANCELLED'
            payment_record = UserPaymentRecord(tid = tid, booking_id = booking_id, user_id = user_id, price = price,
                                                auth_date = authdate, status = status)
            session.add(payment_record)
            session.commit()
            session.close()

            mix.people_track_charge(user_id, price, {'$time' : dt.datetime.now()})
            mongo_logger.debug('%s paid for credit card' % user_id, extra = {'booking_id' : booking_id, 'tid' : tid, 'price' : price})

            return True, tid
        else:
            print 'An error occurred while request processing...'
            print result['err_code'], result['err_msg']
            mongo_logger.error('%s failed to paid for credit card' % user_id, extra = {'booking_id' : booking_id, 'err' : result['err_msg']})
            return False, result['err_msg']

    except Exception, e:
        print_err_detail(e)
        mongo_logger.error('%s failed to paid for credit card' % user_id, extra = {'booking_id' : booking_id, 'err' : str(e)})
        return False, str(e)


def request_unpaid_charge(user_id, user_name, amount, interest, quota):
    try:
        request_url = '%s:%d/homemaster_payment/request_payment_quota' % (PAYMENT_HOST, PAYMENT_PORT)
        params = {'id' : user_id, 'name' : user_name, 'price' : amount, 'product_name' : '미납결제', 'interest' : interest, 'quota' : quota}

        response = requests.post(request_url, data = params)
        result = json.loads(response.text)

        mongo_logger = get_mongo_logger()
        mix = get_mixpanel()

        if result['response'] == Response.SUCCESS:
            # upate request payment record
            tid = result['tid']
            authdate = result['authdate']

            session = Session()
            payment_record = ManualPaymentRecord(user_id = user_id, amount = amount, auth_date = authdate, interest = interest, quota = quota)
            session.add(payment_record)
            session.commit()
            session.close()

            mix.people_track_charge(user_id, amount, {'$time' : dt.datetime.now()})
            mongo_logger.debug('%s paid for unpaid ' % user_id, extra = {'price' : amount})

            return True, tid
        else:
            print 'An error occurred while request processing...'
            print result['err_code'], result['err_msg']
            mongo_logger.error('%s failed to paid for unpaid' % user_id, extra = {'err' : result['err_msg']})
            return False, result['err_msg']

    except Exception, e:
        print_err_detail(e)
        mongo_logger.error('%s failed to paid for unpaid' % user_id, extra = {'err' : str(e)})
        return False, str(e)


def request_charge(user_id, user_name, amount):
    try:
        request_url = '%s:%d/homemaster_payment/request_payment_new' % (PAYMENT_HOST, PAYMENT_PORT)
        params = {'id' : user_id, 'name' : user_name, 'price' : amount, 'product_name' : 'charge_for_cancel'}

        response = requests.post(request_url, data = params)
        result = json.loads(response.text)

        mongo_logger = get_mongo_logger()
        mix = get_mixpanel()

        if result['response'] == Response.SUCCESS:
            # upate request payment record
            tid = result['tid']
            authdate = result['authdate']

            session = Session()

            charge_record = UserChargeRecord(user_id = user_id, tid = tid, amount = amount, auth_date = authdate)
            session.add(charge_record)
            session.commit()
            session.close()

            mix.people_track_charge(user_id, amount, {'time' : dt.datetime.now()})
            mongo_logger.debug('%s charged for canceling before passing 2 months' % user_id, extra = {'amount' : amount})

            return True, tid
        else:
            print 'An error occurred while charging processing...'
            print result['err_code'], result['err_msg']
            mongo_logger.error('%s failed to charged for canceling before passing 2 months' % user_id, extra = {'err' : result['err_msg']})
            return False, result['err_msg']


    except Exception, e:
        print_err_detail(e)
        mongo_logger.error('%s failed to charged for canceling before passing 2 months' % user_id, extra = {'err' : str(e)})
        return False, str(e)

def cancel_payment(user_id, booking_id, amount, partial, cancel_msg = 'refund'):
    try:
        request_url = '%s:%d/homemaster_payment/cancel_payment' % (PAYMENT_HOST, PAYMENT_PORT)

        session = Session()

        # get tid from booking_id
        row = session.query(Booking).filter(Booking.id == booking_id).one()
        tid = row.tid
        session.close()

        params = {'id' : user_id, 'tid' : tid, 'amount' : int(amount), 'partial' : partial, 'cancel_msg' : cancel_msg}

        response = requests.post(request_url, data = params)
        result = json.loads(response.text)

        mongo_logger = get_mongo_logger()
        mix = get_mixpanel()

        print result
        if 'response' in result and result['response'] == Response.SUCCESS:
            mix.people_track_charge(user_id, (-1 * amount), {'time' : dt.datetime.now()})
            mongo_logger.debug('%s cancel charged for credit card' % user_id, extra = {'booking_id' : booking_id, 'tid' : tid, 'amount' : amount, 'partial' : partial})
            return True, ''
        else:
            print 'An error occurred while cancel processing...'
            err_msg = ''
            if 'err_msg' in result:
                err_msg = result['err_msg']

            mongo_logger.error('%s failed to cancel charged for credit card' % user_id, extra = {'booking_id' : booking_id, 'err' : err_msg})
            return False, err_msg

    except Exception, e:
        print_err_detail(e)
        mongo_logger.error('%s failed to cancel charged for credit card' % user_id, extra = {'booking_id' : booking_id, 'err' : str(e)})
        return False, str(e)



def cancel_payment_new(user_id, booking_id, amount, partial, appointment_type, cancel_msg = 'refund'):
    try:
        request_url = '%s:%d/homemaster_payment/cancel_payment_new' % (PAYMENT_HOST, PAYMENT_PORT)

        session = Session()

        # get tid from booking_id
        row = session.query(Booking).filter(Booking.id == booking_id).one()
        tid = row.tid
        session.close()

        params = {'id' : user_id, 'tid' : tid, 'amount' : int(amount), 'partial' : partial, 'appointment_type' : appointment_type, 'cancel_msg' : cancel_msg}

        response = requests.post(request_url, data = params)
        result = json.loads(response.text)

        mongo_logger = get_mongo_logger()
        mix = get_mixpanel()

        print result
        if 'response' in result and result['response'] == Response.SUCCESS:
            mix.people_track_charge(user_id, (-1 * amount), {'time' : dt.datetime.now()})
            mongo_logger.debug('%s cancel charged for credit card' % user_id, extra = {'booking_id' : booking_id, 'tid' : tid, 'amount' : amount, 'partial' : partial})
            return True, ''
        else:
            print 'An error occurred while cancel processing...'
            print result['err_code'], result['err_msg']
            mongo_logger.error('%s failed to cancel charged for credit card' % user_id, extra = {'booking_id' : booking_id, 'err' : result['err_msg']})
            return False, result['err_msg']

    except Exception, e:
        print_err_detail(e)
        mongo_logger.error('%s failed to cancel charged for credit card' % user_id, extra = {'booking_id' : booking_id, 'err' : str(e)})
        return False, str(e)


def request_payment_web(user_id, user_name, amount):
    try:
        request_url = '%s:%d/homemaster_payment/request_payment_new' % (PAYMENT_HOST, PAYMENT_PORT)
        params = {'id' : user_id, 'name' : user_name, 'price' : amount, 'product_name' : 'WEB_PAID'}

        response = requests.post(request_url, data = params)
        result = json.loads(response.text)

        mongo_logger = get_mongo_logger()
        mix = get_mixpanel()

        if result['response'] == Response.SUCCESS:
            # upate request payment record
            tid = result['tid']
            authdate = result['authdate']

            mix.people_track_charge(user_id, amount, {'time' : dt.datetime.now()})
            mongo_logger.debug('web immediate payment', extra = {'amount' : amount,
                                                                'tid' : tid,
                                                                'authdate' : authdate})

            return True, tid
        else:
            print 'An error occurred while charging processing...'
            print result['err_code'], result['err_msg']
            mongo_logger.error('failed to web immediate payment',
                                                    extra = {'err' : result['err_msg']})
            return False, result['err_msg']


    except Exception, e:
        print_err_detail(e)
        mongo_logger.error('failed to web immediate payment',
                                                    extra = {'err' : str(e)})
        return False, str(e)
