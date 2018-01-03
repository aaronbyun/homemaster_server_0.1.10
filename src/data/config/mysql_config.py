#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

try:
    from utils.secrets import DB_ID, DB_PWD, DB_HOST, DB_PORT, DB_NAME
except ImportError:
    DB_ID = ''
    DB_PWD = ''
    DB_HOST = ''
    DB_PORT = 0
    DB_NAME = ''

def get_connection_string():
    return 'mysql+mysqldb://%s:%s@%s:%s/%s?charset=utf8mb4' % (DB_ID, DB_PWD, DB_HOST, DB_PORT, DB_NAME)

def get_biz_connection_string():
    return 'mysql+mysqldb://%s:%s@%s:%s/%s?charset=utf8' % (DB_ID, DB_PWD, DB_HOST, DB_PORT, 'biztalk')