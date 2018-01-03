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
from data.model.data_model import Master, Manager, MasterPreferedArea, MasterTimeSlot
from data.dao.masterdao import MasterDAO
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

class MasterInfoHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        master_id = self.get_argument('master_id', '')

        ret = {}

        try:
            session = Session()
            masterdao = MasterDAO()

            try:
                row = session.query(Master, Manager, func.group_concat(MasterPreferedArea.prefered_gu)) \
                         .join(Manager, Master.manager_id == Manager.id) \
                         .outerjoin(MasterPreferedArea, MasterPreferedArea.master_id == Master.id) \
                         .filter(Master.id == master_id) \
                         .group_by(Master.id) \
                         .one()

            except NoResultFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_no_record'])
                return

            result = session.query(Master, MasterTimeSlot) \
                            .join(MasterTimeSlot, Master.id == MasterTimeSlot.master_id) \
                            .filter(Master.id == master_id) \
                            .order_by(MasterTimeSlot.day_of_week) \
                            .all()

            mid = row.Master.id

            rating_clean, rating_master = masterdao.get_master_rating(mid)
            total_salary = masterdao.get_master_total_granted_salary(mid)
            last_month_salary = masterdao.get_master_last_month_granted_salary(mid)
            prefered_area = masterdao.get_master_prefered_area(mid)

            start_times = ['', '', '', '', '', '', '']
            end_times   = ['', '', '', '', '', '', '']

            for r in result:
                dow = int(r.MasterTimeSlot.day_of_week)
                start_times[dow] = str(r.MasterTimeSlot.start_time.hour)
                end_times[dow] = str(r.MasterTimeSlot.end_time.hour)

            working_startdate = masterdao.get_master_working_start_date(mid)
            completed_cleaning_count = masterdao.get_master_completed_cleaning_count(mid)

            master_info = {}
            master_info['master_id']          = row.Master.id
            master_info['name']          = row.Master.name
            master_info['phone']         = row.Master.phone
            master_info['img']           = row.Master.img_url
            master_info['age']         = row.Master.age
            master_info['gender']         = row.Master.gender
            master_info['pet_alergy'] = row.Master.pet_alergy
            master_info['address']       = row.Master.address
            master_info['manager_name']  = row.Manager.name
            master_info['manager_phone']  = row.Manager.phone
            master_info['cardinal']         = row.Master.cardinal
            master_info['level']         = row.Master.level
            master_info['rating_clean'] = float(rating_clean)
            master_info['rating_master'] = float(rating_master)
            master_info['total_salary'] = int(total_salary)
            master_info['last_month_salary'] = int(last_month_salary)
            master_info['prefered_area'] = prefered_area               # comma separated area
            master_info['cs_prefered_area'] = row[2]               # comma separated area
            master_info['start_times']    = ','.join(start_times) # comma start_time
            master_info['end_times']      = ','.join(end_times)   # comma end_time

            master_info['working_startdate']    = working_startdate
            master_info['cleaning_count']    = completed_cleaning_count

            ret['response'] = master_info
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))
