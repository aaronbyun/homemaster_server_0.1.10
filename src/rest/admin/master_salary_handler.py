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
from sqlalchemy import func, or_, and_
from data.session.mysql_session import engine, Session

from data.model.data_model import Booking, Master
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict

class MasterSalaryOnDateHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")

        salary_date = self.get_argument('date', '')

        ret = {}

        salary_date = dt.datetime.strptime(salary_date, '%Y%m%d')

        # 해당 날짜에 마스터 별로 지급되어야 할 목록이 나타남

        try:
            session = Session()
            result = session.query(Booking, Master) \
                        .join(Master, Master.id == Booking.master_id) \
                        .filter(func.date(Booking.start_time) == salary_date) \
                        .filter(Booking.cleaning_status == BC.BOOKING_COMPLETED) \
                        .order_by(Booking.master_id) \
                        .all()

            master_salaries = []
            
            prev_master_id = None
            for row in result:
                master_id = row.Booking.master_id

                if prev_master_id == None or prev_master_id != master_id:
                    master_salary_dict = {} 
                    master_salary_dict['master_id'] = master_id
                    master_salary_dict['master_name'] = row.Master.name
                    master_salary_dict['master_phone'] = row.Master.phone
                    master_salary_dict['salary_on_date'] = float(row.Booking.price_with_task) * 0.8
                    master_salaries.append(master_salary_dict)
                else:
                    master_salary_dict['salary_on_date'] += float(row.Booking.price_with_task) * 0.8

                prev_master_id = master_id
                

            ret['response'] = master_salaries
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))