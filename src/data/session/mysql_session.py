#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from data.config.mysql_config import get_connection_string, get_biz_connection_string

engine = create_engine(get_connection_string(), pool_recycle = 3600, encoding='utf-8')
Session = sessionmaker(bind=engine)

# for biztalk
biz_engine = create_engine(get_biz_connection_string(), pool_recycle = 3600, encoding='utf-8')
BizSession = sessionmaker(bind=biz_engine)