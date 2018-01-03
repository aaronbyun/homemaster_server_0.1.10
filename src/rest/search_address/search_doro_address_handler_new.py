#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import json
import tornado.ioloop
import tornado.web
import re

import datetime as dt
from utils.extract_aptcode import extract
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict

from data.config.mysql_config import get_connection_string
from data.session.mysql_session import engine, Session
from data.model.data_model import DoroAddress, Sido, Sigungu, MasterPreferedArea, Master, MasterTimeSlot
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from data.mixpanel.mixpanel_helper import get_mixpanel
from sqlalchemy import or_

def split_query_term(addr):
    try:
        addr = addr.replace('번지', '').replace('_', '-')
        num_part = re.compile('(\d+)(-?)(\d*)$')

        #name = num_part.sub('', addr).replace(' ', '').strip()
        names = num_part.sub('', addr).strip()
        name = names.split()[-1].strip()
        nums = num_part.findall(addr)

        print addr
        print names

        if name[-1] == u'동' or name[-1] == u'가':
            addrtype = 'jibun'
        else:
            addrtype = 'doro'

        if len(nums) == 0:
            majornum = ''
            minornum = ''
        else:
            majornum = nums[0][0]
            minornum = nums[0][2]

        if minornum == '':
            minornum = '0'

        return addrtype, name, majornum, minornum
    except Exception, e:
        print_err_detail(e)
        return 'doro', '', '', ''

class DoroAddressSearchHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        uid            = self.get_argument('user_id', '')
        sido            = self.get_argument('sido', '')
        addr            = self.get_argument('addr', '')

        ret = {}

        mix = get_mixpanel()

        addrtype, name, majornum, minornum = split_query_term(addr)

        available = 0 # -1 - no, 0 - unavailable, 1 - available
        addresses = self.search_doro_address(addrtype, sido, name, majornum, minornum)

        if len(addresses) > 0:
            sido = addresses[0]['sido']
            sigungu = addresses[0]['sigungu']

            available = self.get_availability(sido, sigungu)
        else:
            available = -1

        if available != 1 and uid != '':
            mix.track(uid, 'cannot add address', {'time' : dt.datetime.now(), 'sido' : sido, 'address' : addr, 'code' : available})
        else:
            mix.track(uid, 'find address', {'time' : dt.datetime.now(), 'sido' : sido, 'address' : addr, 'code' : available})
        ret['response'] = {'addresses' : addresses, 'available' : available}
        self.set_status(Response.RESULT_OK)
        self.write(json.dumps(ret))


    def get_availability(self, sido, sigungu):
        available = 1

        try:
            session = Session()
            row = session.query(Sido).filter(Sido.name == sido).one()
            sido_id = row.id

            row = session.query(Sigungu).filter(Sigungu.sido_id == sido_id).filter(Sigungu.name == sigungu).one()
            sigungu_id = row.id

            prefered_gu = session.query(MasterPreferedArea, Master) \
                                .join(Master, MasterPreferedArea.master_id == Master.id) \
                                .filter(MasterPreferedArea.prefered_gu == sigungu_id) \
                                .filter(Master.active == 1) \
                                .count()

            print prefered_gu
            if prefered_gu == 0:
                available = 0

        except NoResultFound, e:
            available = 0

        except MultipleResultsFound, e:
            available = 0

        except Exception, e:
            print_err_detail(e)
            available = -1
        finally:
            session.close()
            return available


    # http://121.134.224.40:8080/doro_address?addrtype=doro&sido=%EA%B2%BD%EA%B8%B0%EB%8F%84&name=%ED%8C%90%EA%B5%90%EB%A1%9C&buildingname=2%EB%8B%A8%EC%A7%80
    #
    def search_doro_address(self, addrtype, sido, name, majornum, minornum):
        doro_addresses = []

        try:
            session = Session()
            if addrtype == 'doro':
                query = session.query(DoroAddress).filter(DoroAddress.sido == sido, DoroAddress.doro_name == name)

                if not majornum == '':
                    if not minornum == '0':
                        query = query.filter(DoroAddress.b_main_no == int(majornum), DoroAddress.b_minor_no == int(minornum))
                    else:
                        query = query.filter(DoroAddress.b_main_no == int(majornum))

                result = query.group_by(DoroAddress.doro_code, DoroAddress.b_main_no, DoroAddress.b_minor_no).order_by(DoroAddress.sido, DoroAddress.sigungu, DoroAddress.doro_name, DoroAddress.b_main_no, DoroAddress.b_minor_no).all()

            elif addrtype == 'jibun':
                if name[-1] == u'동':
                    name = re.sub('\d+', '', name) # 오류3동 -> 오류동

                if name == '발산동': # 특별 케이스 -_-
                    query = session.query(DoroAddress).filter(DoroAddress.sido == sido, or_(DoroAddress.dong == '내발산동', DoroAddress.dong == '외발산동'))
                    query2 = session.query(DoroAddress).filter(DoroAddress.sido == sido, DoroAddress.ad_dong_name == name)
                else:
                    query = session.query(DoroAddress).filter(DoroAddress.sido == sido, DoroAddress.dong.like(name + '%'))
                    query2 = session.query(DoroAddress).filter(DoroAddress.sido == sido, DoroAddress.ad_dong_name.like(name + '%'))


                if not majornum == '':
                    if not minornum == '0':
                        query = query.filter(DoroAddress.beonji == int(majornum), DoroAddress.ho == int(minornum))
                        query2 = query2.filter(DoroAddress.beonji == int(majornum), DoroAddress.ho == int(minornum))
                    else:
                        query = query.filter(DoroAddress.beonji == int(majornum))
                        query2 = query2.filter(DoroAddress.beonji == int(majornum))
                    query = query.union(query2)
                    result = query.group_by(DoroAddress.doro_code, DoroAddress.b_main_no, DoroAddress.b_minor_no).order_by(DoroAddress.sido, DoroAddress.sigungu, DoroAddress.doro_name, DoroAddress.b_main_no, DoroAddress.b_minor_no).all()
                else:
                    query = query.union(query2)
                    result = query.group_by(DoroAddress.sigungu, DoroAddress.dong).order_by(DoroAddress.sido, DoroAddress.sigungu, DoroAddress.dong).all()

                    for row in result:
                        sido = row.sido
                        sigungu = row.sigungu
                        doro_name = row.doro_name
                        dong = row.dong

                        address = '%s %s %s' % (sido, sigungu, dong)
                        doro_addresses.append({'full_address' : address, 'jibun_address' : address, 'sido' : sido, 'sigungu' : sigungu, 'doro_name' : doro_name, 'major_no' : 0, 'minor_no' : 0, 'building_name' : ''})

                    return doro_addresses


            for row in result:
                sido = row.sido
                sigungu = row.sigungu
                dong = row.dong
                ri = row.ri
                doro_name = row.doro_name
                doro_code = row.doro_code
                majornum = row.b_main_no
                minornum = row.b_minor_no
                building_name = row.sigungu_building_name
                share = row.share
                san = row.san
                beonji = row.beonji
                ho = row.ho

                jibun_address_1 = '%s %s %s' % (sido, sigungu, dong)

                if ho == 0:
                    jibun_address_2 = '%d' % beonji
                else:
                    jibun_address_2 = '%d-%d' % (beonji, ho)

                if building_name == None or building_name == '':
                    jibun_address = '%s %s' % (jibun_address_1, jibun_address_2.strip())
                else:
                    jibun_address = '%s %s (%s)' % (jibun_address_1, jibun_address_2.strip(), building_name)


                address_1 = ''
                address_2 = ''
                address_3 = ''

                if ri == '':
                    address_1 = '%s %s' % (sido, sigungu)
                    if share == '1':
                        address_3 = '(%s, %s)' % (dong, building_name)
                    else:
                        address_3 = '(%s)' % dong
                else:
                    address_1 = '%s %s %s' % (sido, sigungu, dong)
                    if share == '1':
                        address_3 = '(%s)' % building_name

                if minornum == 0:
                    address_2 = '%s %d' % (doro_name, majornum)
                else:
                    address_2 = '%s %d-%d' % (doro_name, majornum, minornum)

                address = '%s %s%s' % (address_1, address_2, address_3)
                doro_addresses.append({'full_address' : address.strip(), 'jibun_address' : jibun_address, 'sido' : sido, 'sigungu' : sigungu, 'doro_name' : doro_name, 'major_no' : majornum, 'minor_no' : minornum, 'building_name' : building_name})

        except Exception, e:
            session.rollback()
            doro_addresses = None
            print_err_detail(e)

            return None
        finally:
            session.close()

        return doro_addresses


if __name__ == '__main__':
    a, b, c, d = split_query_term(u'야탑3동 372-1')
    print a, b, c, d

    print re.sub('\d+', '', '오류3동')
