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
import rest.booking.booking_constant as BC
from sqlalchemy import func
from data.session.mysql_session import engine, Session
from data.model.data_model import Master, MasterTimeSlot, MasterPreferedArea, MasterAccount
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from cron.master_schedule_date_builder import ScheduleBuilder
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

try:
    from utils.secrets import __UPLOADS__, IMG_SERVER
except ImportError:
    __UPLOADS__ = '/home/'
    IMG_SERVER = 'localhost'


class ModifyAccountNoHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        master_id       = self.get_argument('master_id', '')
        bank_name       = self.get_argument('bank_name', '')
        account_no      = self.get_argument('account_no', '')

        # convert type
        print bank_name, account_no

        try:
            ret = {}
            
            session = Session()

            result = session.query(MasterAccount) \
                            .filter(MasterAccount.master_id == master_id) \
                            .one()
            # add account
            bank_dict = BC.bank_dict

            result.bank_code = bank_dict[bank_name]
            result.account_no = account_no
            result.bank_name = bank_name

            session.commit()

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

        except NoResultFound, e:
            session.close()
            self.set_status(Response.RESULT_OK)
            add_err_message_to_response(ret, err_dict['err_no_record'])
            return

        except MultipleResultsFound, e:
            session.close()
            self.set_status(Response.RESULT_OK)
            add_err_message_to_response(ret, err_dict['err_multiple_record'])
            return

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()
            self.write(json.dumps(ret))
