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
import booking.booking_constant as BC
from sqlalchemy import func
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking
from data.dao.masterdao import MasterDAO
from data.dao.userdao import UserDAO
from data.dao.addressdao import AddressDAO
from data.intermediate.value_holder import IntermediateValueHolder
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from utils.datetime_utils import convert_datetime_format, time_to_minutes, timedelta_to_time

class ChangeMasterOnAllScheduleHandler(tornado.web.RequestHandler):
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

            request_id              = row.request_id
            uid                     = row.user_id 
            master_id_to_change     = row.master_id
            org_start_time          = row.start_time
            org_end_time            = row.estimated_end_time
            appointment_type        = row.appointment_type
            appointment_index       = row.appointment_index
            have_pet                = row.havepet
            master_gender           = row.master_gender

            taking_time_in_minutes = time_to_minutes(timedelta_to_time(org_end_time - org_start_time))

            address, geohash5, geohash6 = userdao.get_user_address(uid)
            gu_id = addrdao.get_gu_id(address)

            dates = [int(dt.datetime.strftime(org_start_time + dt.timedelta(days = i * BC.DAYS_IN_A_WEEK * (4 / appointment_type)), '%Y%m%d'))  for i in xrange(4)]

            time_range_begin     = org_start_time.hour 
            time_range_begin_min = org_start_time.minute
            time_range_end       = org_start_time.hour 
            time_range_end_min   = org_start_time.minute

            print dates
            print gu_id 
            print time_range_begin, time_range_end
            print have_pet
            print master_gender
            print new_master_id

            schedule_by_date_list = masterdao.get_master_schedule_by_dates(gu_id, have_pet, master_gender, dates, new_master_id)
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
                print 'Booking group', request_id, ' WAS NOT ... successfully updated to master_id : ', new_master_id
                
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_no_hm_at_that_time'])
                return     

            else:
                booking_group = session.query(Booking) \
                                        .filter(Booking.request_id == request_id) \
                                        .filter(Booking.appointment_index >= appointment_index) \
                                        .all()

                for row in booking_group:
                    row.master_id = result[0]['mid']

                booking_group2 = session.query(Booking) \
                                        .filter(Booking.request_id == request_id) \
                                        .filter(Booking.appointment_index < appointment_index) \
                                        .all()

                for row in booking_group2:
                    row.is_master_changed = 1

                session.commit()

                holder.remove(store_key)
                for sk in search_keys:
                    holder.remove(sk)

                ret['response'] = Response.SUCCESS
                self.set_status(Response.RESULT_OK)

                print 'Booking group', request_id, ' was successfully updated to master_id : ', new_master_id
                
        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))