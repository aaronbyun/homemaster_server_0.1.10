#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import requests
import uuid
import datetime as dt
import json
import uuid
from sqlalchemy import and_, desc, or_, func, not_
from rest.booking import booking_constant as BC
from err.error_handler import print_err_detail, err_dict
from data.session.mysql_session import engine, Session
from data.model.data_model import Master, MasterAccount

try:
    from utils.secrets import TOSS_KEY
except ImportError:
    TOSS_KEY = ''


def send_money(bank_code, bank_account_no, amount, note):
    toss_url = 'https://toss.im/fb/api/v1/company/deposits'

    headers = {'Accept': 'application/json', 'Content-Type' : 'application/x-www-form-urlencoded'}
    data = {}
    data['key']                     = TOSS_KEY
    data['companyTxNo']             = str(uuid.uuid4())
    data['bankCode']                = bank_code
    data['bankAccountNo']           = bank_account_no
    data['amount']                  = amount
    data['withdrawAccountSummary']  = 'weekly_salary_{}'.format(dt.datetime.strftime(dt.datetime.now(), '%Y%m%d'))
    data['depositAccountSummary']   = note

    response = requests.post(toss_url, data = data, headers = headers)
    response = json.loads(response.text)

    if response['status'] == 200:
        if response['deposit']['status'] == 'SUCCESS':
            return 'SUCCESS', '', response['deposit']['amount'], response['tx']['balance']
        else:
            return 'FAIL', '', response['deposit']['amount'], response['tx']['balance']

    return 'FAIL', response['message'], response['deposit']['amount'], -1

def check_all_master_account():
    session = Session()
    try:
        result = session.query(Master, MasterAccount) \
                        .join(MasterAccount, Master.id == MasterAccount.master_id) \
                        .filter(Master.active == 1) \
                        .all()

        for row in result:
            print row.Master.name, row.Master.phone, check_account(row.MasterAccount.account_no, row.MasterAccount.bank_code)

    except Exception, e:
        print_err_detail(e)

    finally:
        session.close()

def check_account(account_no, bank_code):
    toss_url = 'https://toss.im/fb/api/v1/company/bankaccounts'

    headers = {'Accept': 'application/json', 'Content-Type' : 'application/x-www-form-urlencoded'}
    data = {}
    data['key']                     = TOSS_KEY
    data['companyTxNo']             = str(uuid.uuid4())
    data['bankCode']                = bank_code
    data['bankAccountNo']           = account_no

    response = requests.post(toss_url, data = data, headers = headers)
    response = json.loads(response.text)


    print response['account']['status'], response['account']['message']
    return response['account']['status'], response['account']['message']


if __name__ == '__main__':
    print send_money('4', '49030204009840', 1000, 'test test')
    print send_money('4', '49030204009840', 100000, 'test test')
    print send_money('4', '490302040098401', 1000, 'test test')
    #print check_account('15091029459507', '81')
    #print check_account('121512023441', '11')
    #check_all_master_account()
