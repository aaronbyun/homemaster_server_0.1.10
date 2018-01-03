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
from data.model.data_model import User, Master, Booking, MasterPreferedArea, UserDefaultAddress
from data.dao.userdao import UserDAO
from data.dao.addressdao import AddressDAO
from data.encryption import aes_helper as aes
from response import Response
from response import add_err_message_to_response
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from err.error_handler import print_err_detail, err_dict


class GetMasterNamesHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        user_id         = self.get_argument('user_id', '')        
        havepet         = self.get_argument('havepet', '')
        master_gender   = self.get_argument('master_gender', '')

        havepet = int(havepet)
        master_gender = int(master_gender)

        ret = {}

        try:
            session = Session()
            userdao = UserDAO()
            addressdao = AddressDAO()

            masters = []

            row = session.query(UserDefaultAddress) \
                        .filter(UserDefaultAddress.user_id == user_id) \
                        .one()

            address, _, _   = userdao.get_user_address_by_index(user_id, row.address_idx)

            gu_id           = addressdao.get_gu_id(address)

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
