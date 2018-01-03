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
from data.session.mysql_session import engine, Session
from response import Response
from data.intermediate.value_holder import IntermediateValueHolder
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from data.mixpanel.mixpanel_helper import get_mixpanel

class RecommendNoHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        user_id     = self.get_argument('user_id', '')
        store_key   = self.get_argument('store_key', '')
        search_keys = self.get_argument('search_keys', '')

        print 'dismiss schedule *****'
        print user_id
        print store_key
        print search_keys

        # convert
        search_keys = search_keys.split(',')

        ret = {}

        mix = get_mixpanel()

        try:
            holder = IntermediateValueHolder()

            holder.remove(store_key)
            for sk in search_keys:
                holder.remove(sk)

            if user_id != '':
                mix.track(user_id, 'dismiss schedule', {'time' : dt.datetime.now()})

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

            print 'recommendation was disappeared....'

        except Exception, e:
            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])
        finally:
            self.write(json.dumps(ret))
