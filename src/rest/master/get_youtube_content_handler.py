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
import pytz
from sqlalchemy import desc
from response import Response
from response import add_err_message_to_response
from data.dao.userdao import UserDAO
from data.encryption import aes_helper as aes
from data.session.mysql_session import engine, Session
from data.model.data_model import Master, EduYoutubeMovie
from err.error_handler import print_err_detail, err_dict
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from utils.datetime_utils import convert_datetime_format2

# /all_master_claim
class GetYouTubeContentHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        master_id       = self.get_argument('master_id', '')

        print master_id

        # 0 - remove completely, 2 - cannot get works, but still showed up in list

        ret = {}

        try:
            session = Session()
            row = session.query(Master).filter(Master.id == master_id).one() #등록된 마스터인지 확인 쿼리

            results = session.query(EduYoutubeMovie) \
                            .all()

            youtube_contents = []
            youtube_content = {}

            for result in results:
                youtube_contents.append(result.content)

            youtube_content['contents'] = youtube_contents 

            ret['response'] = youtube_content
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()
            self.write(json.dumps(ret))
