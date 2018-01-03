#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import json
import requests
import tornado.ioloop
import tornado.web
import base64
import uuid
import hashlib
import requests
import xmltodict
import pickle
import itertools
import datetime as dt
import booking.booking_constant as BC
from hashids import Hashids
from schedule.schedule_helper import HMScheduler
from nptime import nptime
from utils.datetime_utils import time_to_str, timedelta_to_time, time_to_minutes
from utils.geo_utils import get_moving_time
from data.session.mysql_session import engine, Session
from data.intermediate.value_holder import IntermediateValueHolder
from data.model.data_model import User, OrderID11st, Booking
from data.dao.userdao import UserDAO
from data.dao.addressdao import AddressDAO
from data.dao.masterdao import MasterDAO
from err.error_handler import print_err_detail, err_dict
from response import Response
from data.intermediate.value_holder import IntermediateValueHolder
from response import add_err_message_to_response, add_err_ko_message_to_response
from sqlalchemy import or_, func
from sqlalchemy.exc import IntegrityError
from data.encryption import aes_helper as aes
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel
from utils.time_price_info import get_time_price, get_additional_task_time_price
from sender.jandi_sender import send_jandi

try:
    from utils.secrets import API_11ST_KEY
except ImportError:
    API_11ST_KEY = 'b70290f8f780afc362554504c126fba6'


class Booking11stChecker(object):
    def __init__(self):
        pass

    def check_11st_new_orders_by_period(self, start_date, end_date):
        try:
            headers = {'openapikey' : API_11ST_KEY}
            url = 'https://api.11st.co.kr/rest/ordservices/complete/%s/%s' % (start_date, end_date)
            r = requests.get(url, headers = headers)

            ret = dict(xmltodict.parse(r.text))
            ret = ret['ns2:orders']
            del ret['@xmlns:ns2']

            if 'ns2:order' in ret:
                orders = ret['ns2:order']
                if isinstance(orders, list):
                    return orders, '', ''
                else:
                    return [orders], '', ''

            print ret

            return [], ret['ns2:result_code'], ret['ns2:result_text']
        except Exception, e:
            print_err_detail(e)
            return [], 'err', str(e)

    def check_11st_new_orders(self, start_date):
        end_date = start_date + dt.timedelta(days = 7)

        start_date_param = dt.datetime.strftime(start_date, '%Y%m%d0000')
        end_date_param = dt.datetime.strftime(end_date, '%Y%m%d0000')
        orders = self.check_11st_new_orders_by_period(start_date_param, end_date_param)
        bookings = orders[0]

        grouped_bookings = []
        grps = itertools.groupby(bookings, lambda x:x['ordNo'])
        for key, items in grps:
            print key
            booking = {}
            booking['ordNo'] = key

            ordDt       = ''
            rsvHopeDt   = ''
            ordNm       = ''
            ordPrtblTel = ''
            rcvrNm      = ''
            rcvrPrtblNo = ''
            buyAddr     = ''
            prdNm       = ''
            prdRiousQty = ''
            addDemndCont = ''
            slctPrdOptNm = ''
            dlvNo        = ''
            selPrc       = 0
            baseaddr     = ''
            detailaddr   = ''

            for sub in items:
                for key in sub:
                    print key, sub[key]
                ordDt           = sub['ordDt']
                rsvHopeDt       = sub['rsvHopeDt']
                ordNm           = sub['ordNm']
                ordPrtblTel     = sub['ordPrtblTel']
                rcvrNm          = sub['rcvrNm']
                rcvrPrtblNo     = sub['rcvrPrtblNo']
                buyAddr         = sub['buyAddr']
                prdNm           += sub['prdNm'] + ', '
                prdRiousQty     = sub['prdRiousQty']
                addDemndCont    = sub['addDemndCont']
                if sub['slctPrdOptNm'] != None:
                    slctPrdOptNm    += sub['slctPrdOptNm'] + ', '
                dlvNo           = sub['dlvNo']
                selPrc          += int(sub['ordAmt'])

                baseaddr       = sub['rcvrBaseAddr']
                detailaddr       = sub['rcvrDtlsAddr']

            booking['ordDt']        = ordDt
            booking['rsvHopeDt']    = rsvHopeDt
            booking['ordNm']        = ordNm
            booking['ordPrtblTel']  = rsvHopeDt
            booking['rcvrNm']       = rcvrNm
            booking['rcvrPrtblNo']  = rcvrPrtblNo
            booking['buyAddr']      = buyAddr
            booking['prdNm']        = prdNm.strip()
            booking['prdRiousQty']  = prdRiousQty
            booking['addDemndCont'] = addDemndCont
            booking['slctPrdOptNm'] = slctPrdOptNm
            booking['selPrc']       = selPrc
            booking['dlvNo']       = dlvNo
            booking['rcvrBaseAddr']       = baseaddr
            booking['rcvrDtlsAddr']       = detailaddr

            grouped_bookings.append(booking)

        #print grouped_bookings

        #return orders
        return grouped_bookings, orders[1], orders[2]


if __name__ == '__main__':
    print dt.datetime.now()
    time_query = dt.datetime.now() - dt.timedelta(days = 3)
    query_date = time_query
    time_query = time_query.date()

    session = Session()
    records = session.query(OrderID11st.div_no) \
                    .filter(func.date(OrderID11st.datetime) >= time_query) \
                    .all()

    div_nos = [row[0] for row in records]

    now = dt.datetime.now()

    booking_checker = Booking11stChecker()
    orders, result_code, result_msg = booking_checker.check_11st_new_orders(query_date)

    # 예약 들어간 사항 필터링
    orders = [order for order in orders if order['dlvNo'] not in div_nos]
    for order in orders:
        user_name = order['rcvrNm']
        address = order['rcvrBaseAddr'] + ' ' + order['rcvrDtlsAddr']
        ord_date = order['ordDt']
        prd_name = order['prdNm']

        send_jandi('11ST_BOOKING', '11st 예약 알림', user_name + ' 고객님 예약됨',
                                '{}, {}, {}'.format(address, ord_date, prd_name))
