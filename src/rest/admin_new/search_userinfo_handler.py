#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import json
import tornado.ioloop
import tornado.web
import uuid
import datetime as dt
from sqlalchemy import and_, or_, func
from data.session.mysql_session import engine, Session
from data.model.data_model import User, UserAddress, UserDefaultAddress, UserMemo
from data.dao.userdao import UserDAO
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.encryption import aes_helper as aes
from sqlalchemy import desc

class SearchUserInfoHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        search_term = self.get_argument('search_term', '')

        ret = {}

        try:
            session = Session()

            users = []
            userdao = UserDAO()

            if search_term == None or search_term == '' or len(search_term) == 1 or search_term == '010':
                self.set_status(Response.RESULT_OK)
                add_err_ko_message_to_response(ret, '잘못된 파라미터 입니다.')
                return

            total_cnt = session.query(User).count()
            now = dt.datetime.now()

            query = session.query(User, UserAddress, UserMemo) \
                            .outerjoin(UserDefaultAddress, UserDefaultAddress.user_id == User.id) \
                            .outerjoin(UserAddress, and_(UserDefaultAddress.user_id == UserAddress.user_id, UserDefaultAddress.address_idx == UserAddress.user_addr_index)) \
                            .outerjoin(UserMemo, User.id == UserMemo.user_id)


            if search_term != '':
                print 'searching term : ' + search_term
                #search_term = search_term.lower()

                query = query.filter(or_(func.aes_decrypt(func.from_base64(User.name), func.substring(User.salt, 1, 16)).like('%' + search_term + '%'),
                                         func.aes_decrypt(func.from_base64(User.phone), func.substring(User.salt, 1, 16)).like(search_term + '%'),
                                         User.email.like(search_term + '%'),
                                         User.id == search_term))

            result = query.order_by(desc(User.dateofreg)).all()

            for row in result:
                key = userdao.get_user_salt(row.User.email)[:16]
                if key == None or key == '':
                    continue

                crypto = aes.MyCrypto(key)

                user_info = {}
                user_info['user_id']    = row.User.id
                user_info['dateofreg']  = dt.datetime.strftime(row.User.dateofreg, '%Y-%m-%d %H:%M')
                user_info['devicetype'] = row.User.devicetype
                user_info['name']       = crypto.decodeAES(row.User.name)
                user_info['email']      = row.User.email
                user_info['authsource'] = row.User.authsource
                user_info['phone']      = crypto.decodeAES(row.User.phone)
                user_info['gender']     = row.User.gender
                user_info['active']     = row.User.active
                user_info['birthdate']  = crypto.decodeAES(row.User.dateofbirth)
                user_info['default_address'] = crypto.decodeAES(row.UserAddress.address) if row.UserAddress != None else ''
                user_info['default_address_size'] = row.UserAddress.size if row.UserAddress != None else ''
                user_info['default_address_kind'] = row.UserAddress.kind if row.UserAddress != None else ''
                user_info['memo']       = row.UserMemo.memo if row.UserMemo != None else ''
                user_info['is_b2b']   = row.User.is_b2b
                #user_info['all_addresses'] = userdao.get_all_user_addresses(row.User.id)

                users.append(user_info)

            ret['response'] = {'count' : total_cnt, 'users' : users}
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))
