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
from sqlalchemy import not_, and_, or_, func
from data.session.mysql_session import engine, Session
from data.model.data_model import Master, User, Booking
from data.dao.userdao import UserDAO
from sender.sms_sender import SMS_Sender
from response import Response
from response import add_err_message_to_response, add_err_ko_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.encryption import aes_helper as aes
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

class NoticeSMSHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        subject         = self.get_argument('subject', '')
        content         = self.get_argument('content', '')
        content_type    = self.get_argument('content_type', '')

        print "subject : "      + subject
        print "content : "      + content
        print "content_type : " + content_type

        ret = {}
        phone_numbers = ""
        sms_sender = SMS_Sender()

        try:
            session = Session()
            if content_type == 'all_masters':
                print 'into masters'
                masters = session.query(Master) \
                                 .filter(Master.phone != 'out') \
                                 .filter(Master.active == 1) \
                                 .filter(func.length(Master.phone) < 12) \
                                 .all()

                for master in masters:
                    phone_numbers += master.phone + ","

            elif content_type == 'all_users':
                print 'into users'
                result  = session.query(func.group_concat(func.aes_decrypt(func.from_base64(User.phone), func.substring(User.salt, 1, 16)))) \
                                 .filter(func.length(func.aes_decrypt(func.from_base64(User.phone), func.substring(User.salt, 1, 16))) < 12) \
                                 .filter(User.phone != 'out') \
                                 .filter(User.active == 1) \
                                 .filter(not_(User.email.op('regexp')(r'._$'))) \
                                 .all()

                phone_numbers = result[0][0]

            elif content_type == 'booking_users':
                print 'into booking_users'
                result  = session.query(func.aes_decrypt(func.from_base64(User.phone), func.substring(User.salt, 1, 16))) \
                                 .join(Booking, Booking.user_id == User.id) \
                                 .filter(Booking.cleaning_status == 0) \
                                 .distinct() \
                                 .all()

                for row in result:
                    phone_numbers += row[0] + ","

                print phone_numbers

            sms_sender.send2(mtype = 'lms', to = phone_numbers, subject = subject, text = content)

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

        except NoResultFound, e:
            session.close()
            self.set_status(Response.RESULT_OK)
            add_err_ko_message_to_response(ret, '조건에 만족하는 결과가 존재하지 않습니다.')
            return

        except Exception, e:
            session.rollback()
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()
            self.write(json.dumps(ret))
