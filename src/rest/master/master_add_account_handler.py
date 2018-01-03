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
import pytz
import rest.booking.booking_constant as BC
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from data.session.mysql_session import engine, Session
from data.model.data_model import Master, MasterAccount
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

class MasterAddAccountHandler(tornado.web.RequestHandler):

    def post(self):
        self.set_header("Content-Type", "application/json")

        ret = {}

        master_id       = self.get_argument('master_id', '')
        account_no      = self.get_argument('account_no', '')
        bank_name       = self.get_argument('bank_name', '')

        try:
            session = Session()

            if not bank_name in bank_dict.keys():
                self.set_status(Response.RESULT_OK)
                add_err_ko_message_to_response(ret, bank_name + '은(는) 지원하지 않는 은행입니다.')
                return

            bank_dict = BC.bank_dict

            account_no = account_no.replace('-', '')

            account = MasterAccount(master_id = master_id, account_no = account_no,
                                    bank_code = bank_dict[bank_name], bank_name = bank_name,
                                    datetime = dt.datetime.now())

            session.add(account)
            session.commit()


            print master_id, ' has successfully add account!'

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
