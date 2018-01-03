#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

from err.error_handler import print_err_detail

from data.session.mysql_session import engine, Session
from data.model.data_model import Sigungu, UserAddress, User
from sqlalchemy import and_, or_

class AddressDAO(object):
    def __init__(self):
        pass

    def get_gu_id(self, address):
        try:
            session = Session()
            print address

            splited = address.split()

            if '수원시 영통구' in address: # 정현석 고객님 예외 사항
                return '2442280'

            if '남양주시' in address:
                return '2472010'

            if '구리시' in address:
                return '2471010'

            if '용인시 기흥구' in address:
                return '2446711'

            if '용인시 수지구' in address:
                return '2448110'

            if len(splited) >= 2:
                gu_name = splited[1]

                row = session.query(Sigungu).filter(Sigungu.name == gu_name).first()
                if row != None:
                    return row.id
                else:
                    gu_name = splited[1] + ' ' + splited[2]
                    row = session.query(Sigungu).filter(Sigungu.name == gu_name).first()
                    if row != None:
                        return row.id

        except Exception, e:
            print_err_detail(e)
            return ''

        finally:
            session.close()


    def get_gu_name(self, address):
        try:
            session = Session()
            print address

            splited = address.split()

            if len(splited) >= 2:
                gu_name = splited[1]

                row = session.query(Sigungu).filter(Sigungu.name == gu_name).first()
                if row != None:
                    return row.name
                else:
                    gu_name = splited[1] + ' ' + splited[2]
                    row = session.query(Sigungu).filter(Sigungu.name == gu_name).first()
                    if row != None:
                        return row.name

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()




if __name__ == '__main__':
    addrdao = AddressDAO()
    #print addrdao.get_gu_id(u'경기도 수원시 영통구 매여울로68번길 22 B03호')
