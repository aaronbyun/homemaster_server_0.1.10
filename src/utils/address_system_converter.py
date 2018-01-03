#-*- coding: utf-8 -*-

import requests as req
import sys
from bs4 import BeautifulSoup

reload(sys)
sys.setdefaultencoding('utf-8')

def convert(original_address):
    try:
        url = 'http://www.juso.go.kr/addrlink/addrLinkApi.do?currentPage=1&countPerPage=1&keyword=%s&confmKey=U01TX0FVVEgyMDE1MDYwMTE3MDk0MQ==' % original_address
        res = req.get(url)

        soup = BeautifulSoup(res.text)
        return soup.find('roadaddrpart1').get_text().encode('ISO-8859-1').decode('utf-8')
    except Exception, e:
        print e
        return ''


if __name__ == '__main__':
    print convert('경기도 성남시 분당구 판교동 629')
    print convert('마포구 창전동 149-1')
    print convert('화성시 향남읍 463')



