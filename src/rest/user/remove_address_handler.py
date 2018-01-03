#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import json
import tornado.ioloop
import tornado.web
import uuid
import datetime as dt

from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.dao.userdao import UserDAO
from data.dao.addressdao import AddressDAO
from data.session.mysql_session import engine, Session
from data.model.data_model import UserAddress, UserDefaultAddress, Booking
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from utils.geo_utils import get_latlng_from_address, get_geohash
from data.encryption import aes_helper as aes
from sqlalchemy import and_, or_, func
from rest.booking import booking_constant as BC
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel

class RemoveAddressHandler(tornado.web.RequestHandler):
    def post(self):
        ret = {}

        user_id    = self.get_argument('user_id', '')
        index      = self.get_argument('index', 0)

        index = int(index)

        print user_id, index

        self.set_header("Content-Type", "application/json")

        mongo_logger = get_mongo_logger()
        mix = get_mixpanel()

        try:
            session = Session()

            try:
                default_index = session.query(UserDefaultAddress) \
                    .filter(UserDefaultAddress.user_id == user_id) \
                    .one()

                # 기본 주소이면 삭제 안되도록 함
                if default_index.address_idx == index:
                    print 'default index'
                    session.close()
                    self.set_status(Response.RESULT_OK)
                    add_err_ko_message_to_response(ret, '기본 주소는 삭제 하실 수 없습니다.')
                    return 

            except NoResultFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_no_record'])
                print_err_detail(e)
                return                

            except MultipleResultsFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_multiple_record'])
                print_err_detail(e)
                return

            # 지난 예약 혹은 다가오는 예약에 해당 주소가 연결되어 있다면 삭제가 안되도록 함
            booking_index_count = session.query(Booking) \
                                        .filter(Booking.cleaning_status > BC.BOOKING_CANCELED) \
                                        .filter(Booking.user_id == user_id) \
                                        .filter(Booking.addr_idx == index) \
                                        .count()

            print booking_index_count

            if booking_index_count  > 0:
                session.close()
                self.set_status(Response.RESULT_OK)
                print 'booking'
                add_err_ko_message_to_response(ret, '완료된 예약과, 다가오는 예약의 주소는 삭제 하실 수 없습니다.')
                return 

            session.query(UserAddress) \
                    .filter(UserAddress.user_id == user_id) \
                    .filter(UserAddress.user_addr_index == index) \
                    .delete()

            session.commit()

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

            print user_id, 'remove address', index,  'successfully!'

            mix.track(user_id, 'remove address', {'time' : dt.datetime.now(), 'index' : index})
            mongo_logger.debug('remove address', extra = {'user_id' : user_id, 'index' : index})

        except Exception, e:
            session.rollback()
            add_err_message_to_response(ret, err_dict['err_mysql'])
            self.set_status(Response.RESULT_SERVERERROR)
            print_err_detail(e)
            mongo_logger.error('failed to remove address', extra = {'user_id' : user_id,'err' : str(e)})
        finally:
            session.close()
            self.write(json.dumps(ret))
            return