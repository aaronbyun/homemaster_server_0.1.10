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
from data.dao.userdao import UserDAO
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, User, UserAddress, UserDefaultAddress
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from logger.mongo_logger import get_mongo_logger
from data.mixpanel.mixpanel_helper import get_mixpanel
from sender.sms_sender import send_confirm_text
from data.encryption import aes_helper as aes


class AddBookingExtraInfoHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        bid             = self.get_argument('booking_id', '')
        msg             = self.get_argument('msg', '')
        enterhome       = self.get_argument('enterhome', '')
        enterbuilding   = self.get_argument('enterbuilding', '')
        trash_location  = self.get_argument('trash_location', '')

        print '%%%%'
        print bid
        print msg
        print enterhome
        print enterbuilding
        print trash_location
        print '%%%%'

        ret = {}

        mongo_logger = get_mongo_logger()
        mix = get_mixpanel()

        try:
            session = Session()

            try:
                row = session.query(Booking).filter(Booking.id == bid).one()
            except NoResultFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_no_record'])
                return

            except MultipleResultsFound, e:
                session.close()
                self.set_status(Response.RESULT_OK)
                add_err_message_to_response(ret, err_dict['err_multiple_record'])
                return

            print 'it is....'

            request_id = row.request_id
            uid        = row.user_id

            # update card info
            userdao = UserDAO()
            card_idx = userdao.get_user_default_card_index(uid)

            key = userdao.get_user_salt_by_id(uid)[:16]
            crypto = aes.MyCrypto(key)

            encrypted_enterhome = crypto.encodeAES(str(enterhome))
            encrypted_enterbuilding = crypto.encodeAES(str(enterbuilding))

            booking_ids = []
            result = session.query(Booking).filter(Booking.request_id == request_id).all()
            for row in result:
                row.card_idx = card_idx
                row.message = msg
                row.enterhome = encrypted_enterhome
                row.enterbuilding = encrypted_enterbuilding
                row.trash_location = trash_location

                booking_ids.append(row.id)

            session.commit()

            mix.track(uid, 'add extra', {'time' : dt.datetime.now(), 'user_message' : msg, 'enterhome' : enterhome, 'enterbuilding' : enterbuilding, 'trash_location' : trash_location})
            mongo_logger.debug('add extra', extra = {'user_id' : uid, 'user_message' : msg, 'enterhome' : enterhome, 'enterbuilding' : enterbuilding, 'trash_location' : trash_location})

            for booking_id in booking_ids:
                print 'extra information was added to booking_id :', booking_id


            # text to master
            #send_confirm_text(bid)

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))
