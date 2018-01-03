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
from data.model.data_model import Master, MasterTimeSlot, MasterScheduleByDate
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from cron.master_schedule_date_builder import ScheduleBuilder

class MasterUpdateTimeHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        master_id   = self.get_argument('master_id', '')
        start_hours = self.get_argument('start_hours', '')
        end_hours   = self.get_argument('end_hours', '')

        start_hours = start_hours.split(',')
        end_hours   = end_hours.split(',')

        ret = {}

        try:
            session = Session()

            current_date = dt.datetime.now().date() + dt.timedelta(days=1)

            # if schedule is not active, store it temporarily
            non_active_result = session.query(MasterScheduleByDate) \
                    .filter(MasterScheduleByDate.master_id == master_id) \
                    .filter(MasterScheduleByDate.active == 0) \
                    .all()

            non_active_dates = []
            for row in non_active_result:
                non_active_dates.append(row.date)        

            # remove schedule
            session.query(MasterScheduleByDate) \
                    .filter(MasterScheduleByDate.master_id == master_id) \
                    .filter(MasterScheduleByDate.date >= current_date) \
                    .delete()

            # remove master time slot
            session.query(MasterTimeSlot) \
                    .filter(MasterTimeSlot.master_id == master_id) \
                    .delete()

            session.commit()

            # add new time slots
            for i in xrange(7):
                sh = start_hours[i]
                eh = end_hours[i]

                if sh == '' or eh == '': continue

                sh = int(sh)
                eh = int(eh)

                new_master_slot = MasterTimeSlot(master_id = master_id, day_of_week = i, start_time = dt.time(sh), end_time = dt.time(eh))
                session.add(new_master_slot)

                session.commit()

            # build schedule
            schedule_builder = ScheduleBuilder()
            schedule_builder.update_new_master_schedule_with_active(master_id, non_active_dates)

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

            print master_id, 'successfully updated start and end times...'

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))
