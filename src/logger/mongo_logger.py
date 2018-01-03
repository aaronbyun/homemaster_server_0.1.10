#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')

import logging
from log4mongo.handlers import MongoHandler

try:
    from utils.secrets import MONGO_HOST, MONGO_PORT, MONGO_USER, MONGO_PWD
except ImportError:
    MONGO_HOST = 'localhost'
    DB_PORT = 27017
    MONGO_USER = ''
    MONGO_PWD = ''

def get_mongo_logger():
    mongo_logger = logging.getLogger('hm_logger')
    if not len(mongo_logger.handlers):
        mongo_logger.addHandler(MongoHandler(host=MONGO_HOST, username = MONGO_USER, password = MONGO_PWD))
    mongo_logger.setLevel(logging.DEBUG)
    return mongo_logger
