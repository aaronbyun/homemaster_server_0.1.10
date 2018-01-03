#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

from mixpanel import Mixpanel

try:
    from utils.secrets import MX_TOKEN 
except ImportError:
    MX_TOKEN = 'test'


def get_mixpanel():
    mp = Mixpanel(MX_TOKEN)
    return mp
