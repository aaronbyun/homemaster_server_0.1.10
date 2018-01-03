#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import json
import tornado.ioloop
import tornado.web
import re

from pymongo import MongoClient

from utils.extract_aptcode import extract
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict

try:
    from utils.secrets import MONGO_USER, MONGO_PWD
except ImportError:
    MONGO_HOST = ''
    DB_PORT = ''


class ResidenceHandler(tornado.web.RequestHandler):
    def initialize(self, mongo):
        self.mongo = mongo
        self.db = mongo.location
        self.db.authenticate(MONGO_USER, MONGO_PWD, source = 'location')

    def get(self):
        self.set_header("Content-Type", "application/json")

        district_code = self.get_argument('district_code', '')

        sido            = self.get_argument('sido', '')
        name            = self.get_argument('doro_name', '')
        majornum        = self.get_argument('majornum', '0')
        minornum        = self.get_argument('minornum', '0')
        extra_address = self.get_argument('extra_address', '')
        apartment_code = extract(extra_address)

        print type(name)

        ret = {}

        query = {}
        if apartment_code != '':
            query['r_list.dong'] = apartment_code

        if district_code != '': # search by district code
            query['district_id'] = district_code
        else: # search by doro address
            query['sido']           = sido
            query['doro_name']      = name
            try:
                query['b_major_no']     = int(majornum)
            except Exception, e:
                print_err_detail()
                query['b_major_no']     = 0

            try:
                query['b_minor_no']     = int(minornum)
            except Exception, e:
                print_err_detail()
                query['b_minor_no']     = 0

        try:
            candidates = self.db.residence.find(query)
        except Exception, e:
            print_err_detail(e)

            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mongodb'])
            self.write(json.dumps(ret))
            return

        # make response
        ret['response'] = []

        if candidates.count() > 0:
            items = []
            temp_dict = {}
            for item in candidates:
                unit_size = int(re.sub('\D', '', item['r_type']))

                if not temp_dict.has_key(unit_size):
                    items.append({'unit_size' : unit_size, 'size' : item['size'], 'actual_size' : item['actual_size'], 'room_cnt' : item['room_cnt'], 'bathroom_cnt' : item['bath_cnt'], 'plan' : item['plan_url']})
                    temp_dict[unit_size] = 1

            ret['response'] = items

        self.set_status(Response.RESULT_OK)
        self.write(json.dumps(ret))
