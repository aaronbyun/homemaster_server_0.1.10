#-*- coding: utf-8 -*-

# requirement
# input - address and size
# output - room / bathroom count

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('../..')

import re
import argparse
import requests as req
from datetime import datetime
from bs4 import BeautifulSoup
from utils.address_system_converter import convert

class ResidenceManager(object):
    def __init__(self,):
        self.URL_STATES = 'http://realestate.daum.net/data/getNaviResult.json'
        self.URL_REST_OF = self.URL_STATES + '?areaCode=%s'
        self.URL_RESIDENCE_META = 'http://realestate.daum.net/data/navi/getDanjiPtypeInfo.daum?danjiId=%s&sort=size'
        self.URL_RESIDENCE_PLAN = 'http://realestate.daum.net/data/PlanPrintPhotoList.daum?danjiId=%s&page=%d&row=8&ptype='
        self.URL_RESIDENCE_DETAIL = 'http://realestate.daum.net/data/DanjiPtypeTabDetail.json?danjiId=%s&pCode=%s'
        self.URL_RESIDENCE_EXTRA  = 'http://realestate.daum.net/iframe/maemul/DanjiInfo.daum?danjiId=%s'
        self.URL_RESIDENCE_APT_AND_OFFICETEL = 'http://realestate.daum.net/data/navi/getDanjiList.json?sort=alphabet&direction=asc&areaCode=%s'

        self.MAX_PLAN_ITEMS_PER_PAGE = 8

    def get_states(self):
        try:
            res = req.get(self.URL_STATES)
            return res.json()['sidoList']
        except Exception, e:
            print e
            return []

    def get_cities(self, state):
        try:
            url = self.URL_REST_OF % state
            res = req.get(url)
            return res.json()['guList']
        except Exception, e:
            print e
            return []

    def get_towns(self, city):
        try:
            url = self.URL_REST_OF % city
            res = req.get(url)
            return res.json()['dongList']
        except Exception, e:
            print e
            return []

    def get_districts(self, town):
        try:
            url = self.URL_REST_OF % town
            res = req.get(url)
            return res.json()['danjiList']
        except Exception, e:
            print e
            return []

    def get_apt_and_officetel(self, town):
        try:
            url = self.URL_RESIDENCE_APT_AND_OFFICETEL % town
            res = req.get(url)
            return res.json()
        except Exception, e:
            print e
            return []

    def get_residence_metadata(self, district_id):
        try:
            metas = []

            url = self.URL_RESIDENCE_META % district_id
            res = req.get(url).json()

            for entity in res:
                meta_dic = {}
                meta_dic['r_id']            = entity['pcode']       if 'pcode' in entity else ''
                meta_dic['r_type']          = entity['ptype']       if 'ptype' in entity else ''
                meta_dic['r_type_in_num']   = int(re.search('[0-9]+', meta_dic['r_type']).group(0))
                meta_dic['room_cnt']        = entity['roomCnt']     if 'roomCnt' in entity else 0
                meta_dic['bath_cnt']        = entity['bathCnt']     if 'bathCnt' in entity else 0
                meta_dic['house_cnt']       = int(entity['houseCnt'])    if 'houseCnt' in entity else 0
                meta_dic['category']        = entity['mcateCode']   if 'mcateCode' in entity else ''
                meta_dic['r_list']          = entity['dongCodeList']if 'dongCodeList' in entity else []

                plan = self.get_residence_plan(district_id, 1, meta_dic['r_id'])
                meta_dic['plan_url'] = plan 

                size, actual_size, resident_num = self.get_residence_detail(meta_dic['category'], district_id, meta_dic['r_id'])
                meta_dic['size'] = size
                meta_dic['actual_size'] = actual_size
                meta_dic['resident_num'] = resident_num

                street_address, original_address, move_in_date = self.get_residence_extra(district_id)
                meta_dic['street_addr'] = street_address
                meta_dic['original_addr'] = original_address
                meta_dic['move_in_date'] = move_in_date

                metas.append(meta_dic)

            return metas
        except Exception, e:
            print e
            return {}

    def get_residence_detail(self, category, district_id, residence_id):
        try:
            url = self.URL_RESIDENCE_DETAIL % (district_id, residence_id)
            res = req.get(url).json()

            if category == 'A6':
                raw_sizes = res['content'][u'계약/전용'].split('/')
            else:
                raw_sizes = res['content'][u'공급/전용'].split('/')
            resident_num = res['content'][u'세대수'].replace(u'세대', '')

            if len(raw_sizes) == 2:
                size = raw_sizes[0].replace('㎡', '').strip()
                actual_size = raw_sizes[1].replace('㎡', '').strip()

                return size, actual_size, resident_num

            return 0, 0, resident_num

        except Exception, e:
            print e
            print 'errrerererererer'
            return -1, -1, -1

    def get_residence_extra(self, district_id):
        try:
            url = self.URL_RESIDENCE_EXTRA % district_id
            res = req.get(url)
            soup = BeautifulSoup(res.text)

            addr_div = soup.find('span', attrs={'id' : 'descAddr'})
            if addr_div:
                addr_div2 = addr_div.find('span', attrs={'title' : '지번'})

                a = addr_div.find('a')
                if a:
                    a.extract()
                
                if addr_div2:
                    addr_div2.extract()
                    street_address = addr_div.get_text(strip=True)
                    original_address = '%s %s' % ('#city#', addr_div2.get_text(strip=True))
                else:
                    original_address = addr_div.get_text(strip=True)
                    try:
                        street_address = convert(original_address).partition(' ')[2]
                    except Exception, e:
                        print e
                        print 'err'
                        street_address = ''

            try:
                ul = soup.find('ul', attrs = {'class' : 'list_infomation'})

                if ul:
                    move_in_date = ul.find_all('li')[4].span.get_text()
                    move_in_date = datetime.strptime(move_in_date, '%Y년 %m월')
            except Exception, e:
                move_in_date = ''

            return street_address, original_address, move_in_date

        except Exception, e:
            print e
            print 'err2'
            return '', '', 0


    def get_residence_plan(self, district_id, page_num, residence_id):
        try:
            url = self.URL_RESIDENCE_PLAN % (district_id, page_num)
            res = req.get(url).json()

            plans = res['list']

            if not plans:
                return ''

            matched_plan = filter(lambda plan: plan['pCode'] == residence_id, plans)

            if not matched_plan:
                return self.get_residence_plan(district_id, page_num + 1, residence_id)

            else:
                return matched_plan[0]['pic']

        except Exception, e:
            print e

from pymongo import MongoClient
mongo = MongoClient('localhost', 27017)

states_dic = {u'경기' : u'경기도', u'강원' : u'강원도', u'충북' : u'충청북도', u'충남' : u'충청남도', u'전북' : u'전라남도', 
                  u'전남' : u'전라남도', u'경북' : u'경상북도', u'경남' : u'경상남도', u'서울시' : u'서울특별시', u'세종시' : u'세종특별자치시',
                  u'인천시' : u'인천광역시', u'부산시' : u'부산광역시', u'대구시' : u'대구광역시', u'울산시' : u'울산광역시', 
                  u'광주시' : u'광주광역시', u'대전시' : u'대전광역시', u'제주' : u'제주특별자치도'}


def collect_residence_data():
    am = ResidenceManager()
    #states = am.get_states()

    states = [{'name' : u'서울시', 'value' : '1100000'}]
    
    db = mongo.location2

    # iteration 213 secs
    for state in states:
        cities = am.get_cities(state['value'])
        for city in cities:
            towns = am.get_towns(city['value'])
            for town in towns:
                districts = am.get_apt_and_officetel(town['value'])
                for dist in districts:
                    dist['value'] = dist['danjiId']

                    district_id = dist['value']
                    metadata = am.get_residence_metadata(district_id)

                    for r_meta in metadata:

                        dist['name'] = dist['danjiName']

                        state_name = states_dic[state['name']] if states_dic.has_key(state['name']) else state['name']

                        print dist['name'], state['name'], city['name'], town['name']
                        print r_meta['street_addr'], '지번 :', r_meta['original_addr'] 

                        r_meta['dong'] = town['name']
                        r_meta['sigungu'] = city['name']
                        r_meta['district'] = dist['name']
                        r_meta['district_id'] = dist['value']
                        r_meta['sido'] = state_name
                        r_meta['original_addr'] = r_meta['original_addr'].replace('#city#', city['name'])
                        r_meta['crawled_date'] = datetime.now()

                        street_addr = r_meta['street_addr']
                        whole_doro_name = street_addr.replace(r_meta['sigungu'], '', 1).strip()

                        doro_name_split = whole_doro_name.split()

                        try:
                            r_meta['doro_name'] = doro_name_split[0]

                            doro_num_split = doro_name_split[1].split('-')
                            if len(doro_num_split) == 1:
                                r_meta['b_major_no'] = int(doro_num_split[0])
                                r_meta['b_minor_no'] = 0
                            elif len(doro_num_split) > 1:
                                r_meta['b_major_no'] = int(doro_num_split[0])
                                r_meta['b_minor_no'] = int(doro_num_split[1])

                        except Exception, e:
                            continue


                        #print r_meta
                        exist = db.residence.find_one({'r_id' : r_meta['r_id']})
                        if not exist:
                            db.residence.insert(r_meta)
                        else:
                            print 'data already exist...'

                    print '*' * 80


def collect_address_system():
    am = ResidenceManager()
    db = mongo.location.address

    for state in am.get_states():
        cities = []
        for city in am.get_cities(state['value']):
            cities.append({ 'code' : city['value'], 'name' : city['name'] })

            towns = []
            for town in am.get_towns(city['value']):
                towns.append({'code' : town['value'], 'name' : town['name']})

                districts = []
                for dist in am.get_apt_and_officetel(town['value']):
                    districts.append({'code' : dist['danjiId'], 'name' : dist['danjiName'], 'level' : 'district'})

                item = db.find_one({'code' : town['value']})
                if not item:
                    db.insert({'code' : town['value'], 'name' : town['name'], 'children' : districts, 'level' : 'town'})

            item = db.find_one({'code' : city['value']})
            if not item: 
                db.insert({'code' : city['value'], 'name' : city['name'], 'children' : towns, 'level' : 'city'})

        item = db.find_one({'code' : state['value']})
        if not item:
            state_name = states_dic[state['name']] if states_dic.has_key(state['name']) else state['name']
            db.insert({'code' : state['value'], 'name' : state_name, 'children' : cities, 'level' : 'state'})




if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Collect Residence Data')
    parser.add_argument('--mode', action='store', dest='mode')

    args = parser.parse_args()
    mode = args.mode

    if mode == 'residence':
        collect_residence_data()
    elif mode == 'address':
        collect_address_system()
    elif mode == 'matching': # add sql key with mysql database
        pass
    