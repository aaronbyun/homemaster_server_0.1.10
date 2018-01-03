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
from sqlalchemy import func
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking
from data.dao.masterdao import MasterDAO
from data.dao.userdao import UserDAO
from data.encryption import aes_helper as aes
from data.dao.addressdao import AddressDAO
from data.intermediate.value_holder import IntermediateValueHolder
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from utils.datetime_utils import convert_datetime_format, time_to_minutes, timedelta_to_time

class ChangeMasterOnScheduleHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")

        booking_id = self.get_argument('booking_id', '')
        new_master_id = self.get_argument('new_master_id', '')

        ret = {}

        try:
            session = Session()

            userdao = UserDAO()
            addrdao = AddressDAO()
            masterdao = MasterDAO()

            holder = IntermediateValueHolder()

            row = session.query(Booking).filter(Booking.id == booking_id).one()

            uid                     = row.user_id 
            master_id_to_change     = row.master_id
            org_start_time          = row.start_time
            org_end_time            = row.estimated_end_time
            appointment_type        = 0 # 여기서는 1회 청소로 한다. 편집이기 때문에
            have_pet                = row.havepet
            master_gender           = row.master_gender
            addr_idx                = row.addr_idx

            taking_time_in_minutes = time_to_minutes(timedelta_to_time(org_end_time - org_start_time))

            address, geohash5, geohash6 = userdao.get_user_address_by_index(uid, addr_idx)
            gu_id = addrdao.get_gu_id(address)
            dates = [int(dt.datetime.strftime(org_start_time, '%Y%m%d'))]

            time_range_begin     = org_start_time.hour 
            time_range_begin_min = org_start_time.minute
            time_range_end       = org_start_time.hour 
            time_range_end_min   = org_start_time.minute

            print gu_id, dates
            print time_range_begin
            print time_range_begin_min
            print time_range_end
            print time_range_end_min
            print taking_time_in_minutes

            schedule_by_date_list = masterdao.get_master_schedule_by_dates(gu_id, have_pet, master_gender, dates, new_master_id)

            print schedule_by_date_list

            success, msg, store_key, search_keys, result = masterdao.find_master_by_score(schedule_by_date_list, \
                                                gu_id, \
                                                uid, \
                                                appointment_type, \
                                                dates, \
                                                time_range_begin, \
                                                time_range_begin_min, \
                                                time_range_end, \
                                                time_range_end_min, \
                                                taking_time_in_minutes, \
                                                geohash6)

            if success != 'SUCCESS':
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_no_hm_at_that_time'])
                #self.write(json.dumps(ret)) 

                print booking_id, ' WAS NOT ... successfully updated to master_id : ', new_master_id
                return     
            else:
                row.master_id = result[0]['mid']
                if master_id_to_change != row.master_id:
                    row.is_master_changed = 1

                session.commit()

                holder.remove(store_key)
                for sk in search_keys:
                    holder.remove(sk)

                ret['response'] = Response.SUCCESS
                self.set_status(Response.RESULT_OK)

                print booking_id, ' was successfully updated to master_id : ', new_master_id
                
        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))