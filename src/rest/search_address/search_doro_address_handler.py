#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import json
import tornado.ioloop
import tornado.web

from utils.extract_aptcode import extract
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict

from data.config.mysql_config import get_connection_string
from data.session.mysql_session import engine, Session
from data.model.data_model import DoroAddress

class DoroAddressSearchHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")

        addrtype        = self.get_argument('addrtype', 'doro') # doro, jibun
        sido            = self.get_argument('sido', '')
        name            = self.get_argument('name', '')      # 도로명 주소 - 도로명, 지번주소 - 읍면동 
        majornum        = self.get_argument('majornum', '')  # 도로명 주소 - 건물번호, 지번주소 - 번지
        minornum        = self.get_argument('minornum', '0')
        building_name   = self.get_argument('buildingname', '')

        ret = {}

        name = name.replace(u' ', '').strip()
        building_name = building_name.replace(u' ', '').strip()

        ret['response'] = self.search_doro_address(addrtype, sido, name, majornum, minornum, building_name)
        self.set_status(Response.RESULT_OK)
        self.write(json.dumps(ret))

        print majornum, minornum


    # http://121.134.224.40:8080/doro_address?addrtype=doro&sido=%EA%B2%BD%EA%B8%B0%EB%8F%84&name=%ED%8C%90%EA%B5%90%EB%A1%9C&buildingname=2%EB%8B%A8%EC%A7%80
    # 
    def search_doro_address(self, addrtype, sido, name, majornum, minornum, building_name):
        doro_addresses = []

        try:
            session = Session()
            if addrtype == 'doro':
                query = session.query(DoroAddress).filter(DoroAddress.sido == sido, DoroAddress.doro_name == name)

                if not majornum == '':
                    query = query.filter(DoroAddress.b_main_no == int(majornum), DoroAddress.b_minor_no == int(minornum))
                if not building_name == '':
                    query = query.filter(DoroAddress.sigungu_building_name.like('%'+building_name+'%'))

            elif addrtype == 'jibun':
                query = session.query(DoroAddress).filter(DoroAddress.sido == sido, DoroAddress.dong == name)
                query2 = session.query(DoroAddress).filter(DoroAddress.sido == sido, DoroAddress.ad_dong_name == name)

                if not majornum == '':
                    query = query.filter(DoroAddress.beonji == int(majornum), DoroAddress.ho == int(minornum))
                    query2 = query.filter(DoroAddress.beonji == int(majornum), DoroAddress.ho == int(minornum))
                if not building_name == '':
                    query = query.filter(DoroAddress.sigungu_building_name.like('%'+building_name+'%'))
                    query2 = query.filter(DoroAddress.sigungu_building_name.like('%'+building_name+'%'))

                query = query.union(query2)

            result = query.group_by(DoroAddress.doro_code, DoroAddress.b_main_no, DoroAddress.b_minor_no).all()

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
                doro_addresses.append({'full_address' : address.strip(), 'sido' : sido, 'sigungu' : sigungu, 'doro_name' : doro_name, 'major_no' : majornum, 'minor_no' : minornum})

        except Exception, e:
            session.rollback()
            doro_addresses = None
            print_err_detail(e)

            return None
        finally:
            session.close()

        return doro_addresses