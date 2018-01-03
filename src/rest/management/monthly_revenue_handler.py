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
from data.model.data_model import Booking, Master, User, UserAddress
from data.dao.userdao import UserDAO
from data.encryption import aes_helper as aes
from response import Response
from response import add_err_message_to_response
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from err.error_handler import print_err_detail, err_dict
from utils.datetime_utils import get_month_day_range
from collections import OrderedDict

# /monthly_revenue
class MonthlyRevenueHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        year = self.get_argument('yyyy', 2016)
        month = self.get_argument('mm', 9)

        year = int(year)
        month = int(month)

        first_day, last_day = get_month_day_range(dt.date(year, month, 7))

        ret = {}
        revenue_by_gu = {}

        try:
            session = Session()

            sql = '''select s.name, b.appointment_type as type, sum(price_with_task) + sum(charging_price) + sum(ifnull(p.discount_price, 0)) + sum(ifnull(pb.discount_price, 0)) as revenue
                     from bookings b
                        join users u
                        on b.user_id = u.id
                        join user_addresses a
                        on b.user_id = a.user_id and b.addr_idx = a.user_addr_index
                        join sigungu s
                        on aes_decrypt(from_base64(a.address), substr(u.salt, 1, 16)) like CONCAT('%', s.name, '%')
                        left join promotions p
                        on b.id = p.booking_id
                        left join event_promotion_bookings pb
                        on b.id = pb.booking_id
                        where date(b.start_time) >= :first_day and  date(b.start_time) <= :last_day
                        and u.email not like '%@b2b.com'
                        and b.cleaning_status > -1
                        group by s.name, b.appointment_type
                        order by name, revenue desc'''

            print first_day, last_day

            query_param = {'first_day' : first_day, 'last_day' : last_day}
            result = session.execute(sql, query_param).fetchall()

            prev_gu_name = None

            for row in result:
                item = dict(row)

                gu_name = item['name']
                cleaning_type = item['type']

                if cleaning_type == 0:
                    cleaning_type = '1회'
                elif cleaning_type == 1:
                    cleaning_type = '4주1회'
                elif cleaning_type == 2:
                    cleaning_type = '2주1회'
                elif cleaning_type == 3:
                    cleaning_type = '해보고정기'
                elif cleaning_type == 4:
                    cleaning_type = '매주'

                revenue = int(item['revenue'])

                if gu_name == None or gu_name != prev_gu_name:
                    revenue_by_gu[gu_name] = {cleaning_type : revenue, 'total_revenue' : revenue, 'total' : revenue}
                else:
                    revenue_by_gu[gu_name]['total_revenue'] += revenue
                    revenue_by_gu[gu_name]['total'] = revenue_by_gu[gu_name]['total_revenue']

                    revenue_by_gu[gu_name][cleaning_type] = revenue

                prev_gu_name = gu_name

            for gu in revenue_by_gu:
                for t in revenue_by_gu[gu]:
                    if t != 'total':
                        revenue_by_gu[gu][t] = '{:,}'.format(revenue_by_gu[gu][t])

            revenue_by_gu = OrderedDict(sorted(revenue_by_gu.items(), key = lambda x: -x[1]['total']))

            ret['response'] = revenue_by_gu
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))
