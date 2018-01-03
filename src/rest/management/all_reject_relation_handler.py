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
from sqlalchemy import and_, desc, func
from data.session.mysql_session import engine, Session
from data.model.data_model import RejectRelation, Master, User
from data.dao.userdao import UserDAO
from data.encryption import aes_helper as aes
from response import Response
from response import add_err_message_to_response
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from err.error_handler import print_err_detail, err_dict

# /add_reject_relation
class AllRejectRelationHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        ret = {}

        try:
            session = Session()
            result = session.query(RejectRelation, Master) \
                    .join(User, RejectRelation.user_id == User.id) \
                    .join(Master, RejectRelation.master_id == Master.id) \
                    .order_by(Master.name) \
                    .all()

            reject_relations = []

            for row in result:
                relation = {'master_name' : row.Master.name, 'user_name' : row.User.name}
                reject_relations.append(relation)

            ret['response'] = reject_relations

            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            session.close()
            self.write(json.dumps(ret))
