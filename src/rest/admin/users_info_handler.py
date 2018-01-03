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
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.encryption import aes_helper as aes
from sqlalchemy import desc

class UserSearchHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")

        mode        = self.get_argument('mode', 'week') # today, week, all
        search_term = self.get_argument('search_term', '')

        ret = {}

        now = dt.datetime.now().date()
        week_ago = now - dt.timedelta(days = 7)

        try:
            session = Session()

            users = []
            userdao = UserDAO()

            total_cnt = session.query(User).count()

            query = session.query(User, UserAddress, UserMemo) \
                            .outerjoin(UserDefaultAddress, UserDefaultAddress.user_id == User.id) \
                            .outerjoin(UserAddress, and_(UserDefaultAddress.user_id == UserAddress.user_id, UserDefaultAddress.address_idx == UserAddress.user_addr_index)) \
                            .outerjoin(UserMemo, User.id == UserMemo.user_id)

            if mode == 'week':
                query = query.filter(func.date(User.dateofreg) >= week_ago)
            elif mode == 'today':
                query = query.filter(func.date(User.dateofreg) == now)

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
                    print row.User.email
                    continue

                crypto = aes.MyCrypto(key)

                user_info = {}
                user_info['user_id']    = row.User.id
                user_info['dateofreg']  = dt.datetime.strftime(row.User.dateofreg, '%Y-%m-%d %H:%M')
                user_info['devicetype'] = row.User.devicetype
                user_info['name']       = crypto.decodeAES(row.User.name)
                user_info['email']      = row.User.email
                user_info['phone']      = crypto.decodeAES(row.User.phone)
                user_info['gender']     = row.User.gender
                user_info['birthdate']  = crypto.decodeAES(row.User.dateofbirth)
                user_info['default_address'] = crypto.decodeAES(row.UserAddress.address) if row.UserAddress != None else ''
                user_info['default_address_size'] = row.UserAddress.size if row.UserAddress != None else ''
                user_info['default_address_kind'] = row.UserAddress.kind if row.UserAddress != None else ''
                user_info['memo']       = row.UserMemo.memo if row.UserMemo != None else ''

                #if search_term != '':
                #    if search_term.lower() in user_info['name'].lower() or user_info['phone'] == search_term or user_info['email'] == search_term:
                users.append(user_info)

            #if search_term != '':
            #    users = filter(lambda x : search_term.lower() in x['name'].lower() or x['phone'] == search_term or x['email'] == search_term, users)

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