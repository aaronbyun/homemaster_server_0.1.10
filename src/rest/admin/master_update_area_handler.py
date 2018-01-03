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
from sqlalchemy import func
from data.session.mysql_session import engine, Session
from data.model.data_model import Master, MasterPreferedArea
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict

class MasterUpdateAreaHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        master_id   = self.get_argument('master_id', '')
        region_ids  = self.get_argument('region_ids', '')

        # convert date type
        region_ids  = region_ids.split(',')

        ret = {}

        try:
            session = Session()

            # master prefered area
            session.query(MasterPreferedArea).filter(MasterPreferedArea.master_id == master_id).delete()

            session.commit()

            for rid in region_ids:
                try:
                    rid = int(rid)
                except Exception, e:
                    print e
                    continue

                new_master_area = MasterPreferedArea(master_id = master_id, prefered_gu = rid)
                session.add(new_master_area)

            session.commit()

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

            print master_id, 'successfully updated regions ids...'

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_hm_update_area'])
        finally:
            session.close()
            self.write(json.dumps(ret))
