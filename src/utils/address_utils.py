#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import re
from sqlalchemy import and_, desc, or_, func, not_
from err.error_handler import print_err_detail, err_dict
from data.session.mysql_session import engine, Session
from data.model.data_model import DoroAddress
from err.error_handler import print_err_detail, err_dict


def convert_to_jibun_address(doro_address):
    jibun_address = ''

    session = Session()

    try:
        # 괄호 이후 전부 삭제
        # 숫자 부분 parsing
        # 시도, 시군구, 도로명 주소로 나뉘어 검색
        # 결과 빌드 후 리턴

        try:
            parentheses = doro_address.index('(')

            doro = doro_address[:parentheses]
            rest = doro_address[parentheses:]
        except Exception, e:
            if '로 ' in doro_address:
                d_index = doro_address.index('로 ')
                doro = doro_address[:d_index + 1]
                part = doro_address[d_index + 1:]
                temp = part.split()

                doro = doro + ' ' + temp[0]
                rest = ' '.join(temp[1:])

            elif '길 ' in doro_address:
                d_index = doro_address.index('길 ')
                doro = doro_address[:d_index + 1]
                part = doro_address[d_index + 1:]
                temp = part.split()

                doro = doro + ' ' + temp[0]
                rest = ' '.join(temp[1:])
            else:
                jibun_address = doro_address
                return

        num_re = re.compile('(\d+)(-?)(\d*)$')
        addr_part = num_re.sub('', doro).strip()
        num_part = num_re.findall(doro)

        addr_part = addr_part.split()

        if len(addr_part) == 3:
            sido = addr_part[0]
            sigungu = addr_part[1]
            doro_name = addr_part[2]
        elif len(addr_part) == 4:
            sido = addr_part[0]
            sigungu = addr_part[1] + ' ' + addr_part[2]
            doro_name = addr_part[3]

        main_no = int(num_part[0][0])
        minor_no = num_part[0][2]

        if minor_no == '':
            minor_no = 0
        else:
            minor_no = int(minor_no)

        print sido, sigungu, doro_name, main_no, minor_no, rest

        row = session.query(DoroAddress) \
                .filter(DoroAddress.sido == sido) \
                .filter(DoroAddress.sigungu == sigungu) \
                .filter(DoroAddress.doro_name == doro_name) \
                .filter(DoroAddress.b_main_no == main_no) \
                .filter(DoroAddress.b_minor_no == minor_no) \
                .group_by(DoroAddress.doro_code) \
                .one()

        jibun_address = row.sido + ' ' + row.sigungu + ' ' + row.dong + ' ' + str(row.beonji)
        if row.ho != 0:
            jibun_address += '-' + str(row.ho)
        jibun_address += ' ' + rest
        jibun_address = jibun_address.strip()

    except Exception, e:
        #print_err_detail(e)
        jibun_address = doro_address
        return doro_address

    finally:
        session.close()
        return jibun_address


if __name__ == '__main__':
    addr = convert_to_jibun_address('서울특별시 은평구 은평로 48(신사동) 309호')
    print addr
