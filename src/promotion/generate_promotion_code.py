#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import json
import datetime as dt
import rest.booking.booking_constant as BC
from hashids import Hashids
from data.session.mysql_session import engine, Session
from data.model.data_model import Promotion
from err.error_handler import print_err_detail, err_dict
from random import randint


def generate_promotion_codes(discount_price, start_num, end_num):
    try:
        session = Session()

        for i in xrange(start_num, end_num):
            hashids = Hashids(min_length = 6, salt = 'show' + str(i))
            code = hashids.encode(i)
            print code
            p = Promotion(promotion_code = code, used = 0, discount_price = discount_price, source = 'hm')
            session.add(p)

        session.commit()
    except Exception, e:
        print_err_detail(e)

    finally:
        session.close()


if __name__ == '__main__':
    #generate_promotion_codes(5000, 100000, 104000)
    #generate_promotion_codes(5000, 170000, 173000)
    #generate_promotion_codes(10000, 160000, 163000)
    generate_promotion_codes(20000, 180000, 180500)
    generate_promotion_codes(40000, 190000, 190500)
