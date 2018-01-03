#-*- coding: utf-8 -*-

import re
import sys

reload(sys)
sys.setdefaultencoding('utf-8')

def extract(extra_address):
    if not extra_address or len(extra_address) <= 0: return ''
    
    try:
        addr = extra_address.decode('utf-8')
        converted = re.search(u'[0-9]+(-|동)', addr).group()
        return converted[:len(converted)-1]
    except Exception, e:
        print e
        return ''

if __name__ == '__main__':
    print extract('원마을3단지 305-1702')
    print extract('원마을3단지 305동 1702호')
    print extract('원마을3단지 305동1702호')