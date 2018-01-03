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
from sqlalchemy import func, or_
from data.session.mysql_session import engine, Session
from data.model.data_model import Master, Manager, MasterSalary
from data.dao.masterdao import MasterDAO
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from err.error_handler import print_err_detail, err_dict

class SearchMasterInfoHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        search_term = self.get_argument('search_term', '')

        ret = {}

        try:
            session = Session()
            masterdao = MasterDAO()

            if search_term == None or search_term == '' or len(search_term) == 1 or search_term == '010':
                self.set_status(Response.RESULT_OK)
                add_err_ko_message_to_response(ret, '잘못된 파라미터 입니다.')
                return

            print 'searching master term : ' + search_term

            masters = []
            results  = session.query(Master) \
                                    .filter(or_(Master.phone.like(search_term + '%'), Master.name.like('%' + search_term + '%'))) \
                                    .filter(Master.active != 0) \
                                    .all()

            print results

            total_counts = 0
            for result in results:
                mid = result.id
                print mid
                master_info = {}

                basic = masterdao.get_master_basic_info(mid)
                rating_clean, rating_master = masterdao.get_master_rating(mid)
                total_salary = masterdao.get_master_total_granted_salary(mid)
                last_month_salary = masterdao.get_master_last_month_granted_salary(mid)
                prefered_area = masterdao.get_master_prefered_area(mid)
                start_times, end_times = masterdao.get_master_working_time(mid)

                working_startdate = masterdao.get_master_working_start_date(mid)
                completed_cleaning_count = masterdao.get_master_completed_cleaning_count(mid)

                bank_name, bank_code, account_no = masterdao.get_master_account(mid)

                master_info['master_id']    = mid
                master_info['name']         = basic['name']
                master_info['phone']        = basic['phone']
                master_info['img']          = basic['img']
                master_info['age']          = basic['age']
                master_info['gender']       = basic['gender']
                master_info['address']      = basic['address']
                master_info['pet_alergy']   = basic['pet_alergy']
                master_info['manager_name'] = basic['manager_name']
                master_info['manager_phone'] = basic['manager_phone']
                master_info['cardinal']     = basic['cardinal']
                master_info['level']        = basic['level']
                master_info['need_route']    = basic['need_route']
                master_info['t_size']        = basic['t_size']
                master_info['rating_clean'] = float(rating_clean)
                master_info['rating_master'] = float(rating_master)
                master_info['total_salary'] = int(total_salary)
                master_info['last_month_salary'] = int(last_month_salary)
                master_info['prefered_area'] = prefered_area
                master_info['prefered_area_list'] = [area for area in prefered_area.split(',')]
                master_info['start_times']  = start_times
                master_info['end_times']    = end_times
                master_info['active']       = basic['active']

                master_info['working_startdate']    = working_startdate
                master_info['cleaning_count']    = completed_cleaning_count
                master_info['account'] = {'name' : bank_name, 'code' : bank_code, 'account_no' : account_no}

                masters.append(master_info)
                total_counts += 1

            print masters

            ret['response'] = {'counts' : total_counts, 'masters' : masters }
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))
