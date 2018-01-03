#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import requests as req
import datetime as dt
from pymongo import MongoClient

try:
    from utils.secrets import MONGO_HOST, MONGO_PORT
except ImportError:
    MONGO_HOST = 'localhost'
    DB_PORT = 27017

mongo = MongoClient(MONGO_HOST, MONGO_PORT)

def crawl_seoul_subway_stations():
    url = 'http://map.naver.com/external/SubwayProvide.xml?requestFile=metaData.json&readPath=1000&version=3.9'
    headers = {'User-Agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.86 Safari/537.36'}
    res = req.get(url, headers = headers).json()

    db = mongo.location
    col = db.station

    result = res[0]
    real_info = result['realInfo']


    for station in real_info:
        st_info = {}
        st_info['id']       = station['id']
        st_info['name']     = station['name'] 
        st_info['line_num'] = int(station['logicalLine']['code'])
        st_info['line_name'] = station['logicalLine']['name']

        st_info['location'] = {}
        st_info['latitude'] = float(station['latitude'])
        st_info['longitude'] = float(station['longitude'])
        st_info['location']['type'] = 'Point'
        st_info['location']['coordinates'] = [st_info['longitude'], st_info['latitude'], ]

        col.insert(st_info)
        print station['name'], 'was inserted...' 


if __name__ == '__main__':
    crawl_seoul_subway_stations()
