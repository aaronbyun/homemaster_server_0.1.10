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
from sqlalchemy import and_, desc
from data.session.mysql_session import engine, Session
from data.model.data_model import User, Master, Booking, MasterPreferedArea
from data.dao.userdao import UserDAO
from data.dao.addressdao import AddressDAO
from data.encryption import aes_helper as aes
from response import Response
from response import add_err_message_to_response
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from err.error_handler import print_err_detail, err_dict


class AllMasterNameHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        booking_id = self.get_argument('booking_id', '')

        ret = {}

        try:
            session = Session()
            userdao = UserDAO()
            addressdao = AddressDAO()

            masters = []

            if booking_id == '':
                result = session.query(Master) \
                                .filter(Master.active == 1) \
                                .order_by(Master.name) \
                                .all()

                for row in result:
                    masters.append({'id' : row.id, 'name' : row.name})

                ret['response'] = masters
                self.set_status(Response.RESULT_OK)
                return

            row = session.query(Booking) \
                        .filter(Booking.id == booking_id) \
                        .one()

            user_id         = row.user_id
            address, _, _   = userdao.get_user_address_by_index(user_id, row.addr_idx)

            gu_id           = addressdao.get_gu_id(address)
            havepet         = row.havepet
            master_gender   = row.master_gender

            pet_filter = 2
            if havepet == 1:
                pet_filter = 1

            gender_filter = 2
            if master_gender == 1:
                gender_filter = 0

            result = session.query(Master, MasterPreferedArea) \
                            .join(MasterPreferedArea, Master.id == MasterPreferedArea.master_id) \
                            .filter(Master.active == 1) \
                            .filter(Master.pet_alergy != pet_filter) \
                            .filter(Master.gender != gender_filter) \
                            .filter(MasterPreferedArea.prefered_gu == gu_id) \
                            .order_by(Master.name) \
                            .all()

            for row in result:
                masters.append({'id' : row.Master.id, 'name' : row.Master.name})


            ret['response'] = masters
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))
