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
from data.session.mysql_session import engine, Session
from data.dao.userdao import UserDAO
from data.dao.addressdao import AddressDAO
from data.model.data_model import MasterPreferedArea, Master
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from logger.mongo_logger import get_mongo_logger

class MasterGenderByRegionHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        uid     = self.get_argument('user_id', '')
        master_gender    = self.get_argument('master_gender', 1)

        mongo_logger = get_mongo_logger()
        master_gender = int(master_gender)
        
        if master_gender == 2: # 남자일 경우 남자코드인 0으로 변경
            master_gender = 0

        try:
            session = Session()

            userdao = UserDAO()
            addressdao = AddressDAO()

            address = userdao.get_user_address(uid)[0]
            gu_id = addressdao.get_gu_id(address)

            master_count_by_gender = session.query(MasterPreferedArea, Master) \
                    .join(Master, MasterPreferedArea.master_id == Master.id) \
                    .filter(MasterPreferedArea.prefered_gu == gu_id) \
                    .filter(Master.gender == master_gender) \
                    .filter(Master.active == 1) \
                    .count()

            ret['response'] = {'master_count_by_gender' : master_count_by_gender}
            self.set_status(Response.RESULT_OK)

            print uid, 'request master gender, value of ', master_gender, master_count_by_gender
            mongo_logger.debug('%s request master gender count' % uid, extra={'user_id' : uid, 'master_gender' : master_gender})

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
            mongo_logger.error('%s failed to posted memo' % uid, extra = {'err' : str(e)})
        finally:
            session.close()
            self.write(json.dumps(ret))
        