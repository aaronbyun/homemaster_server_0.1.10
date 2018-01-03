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
from pymongo import MongoClient
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict

try:
    from utils.secrets import MONGO_USER, MONGO_PWD
except ImportError:
    MONGO_HOST = ''
    DB_PORT = ''

class AddressHandler(tornado.web.RequestHandler):
    def initialize(self, mongo):

        self.mongo = mongo
        location = mongo.location
        location.authenticate(MONGO_USER, MONGO_PWD, source = 'location')

        self.db = location.address

    def get(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        area_code = self.get_argument('area_code', '')

        ret = {}

        if area_code == '':
            self.set_status(Response.RESULT_BADREQUEST)
            add_err_message_to_response(ret, u'Invalid parameter('')')
            self.write(json.dumps(ret))
            return

        if area_code == 'state':
            try:
                cursor = self.db.find({'level' : 'state'})
            except Exception, e:
                print_err_detail(e)

                self.set_status(Response.RESULT_SERVERERROR)
                add_err_message_to_response(ret, err_dict['err_mongodb'])
                self.write(json.dumps(ret))
                return

            states = []
            for state in cursor:
                states.append({'name' : state['name'], 'code' : state['code']})

            ret['requested_code'] = area_code
            ret['requested_name'] = ''
            ret['response'] = states
        else:
            try:
                item = self.db.find_one({'code' : area_code})
            except Exception, e:
                print_err_detail(e)

                self.set_status(Response.RESULT_SERVERERROR)
                add_err_message_to_response(ret, err_dict['err_mongodb'])
                self.write(json.dumps(ret))
                return

            ret['requested_code'] = area_code
            ret['requested_name'] = item['name'] if item else ''
            ret['response'] = item['children'] if item else ''

        self.set_status(Response.RESULT_OK)
        self.write(json.dumps(ret))
