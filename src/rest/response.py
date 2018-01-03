#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

class Response(object):
    RESULT_OK           = 200
    RESULT_BADREQUEST   = 400
    RESULT_NOTFOUND     = 404
    RESULT_SERVERERROR  = 500

    SUCCESS    = 'SUCCESS'
    FAIL     = 'FAIL'


def add_err_message_to_response(ret, err):
    ret['response'] = ''
    ret['err_code'] = err['err_code']
    ret['err_msg']  = err['err_msg']

def add_err_ko_message_to_response(ret, msg):
    ret['response'] = ''
    ret['err_code'] = ''
    ret['err_msg']  = msg

def add_err_ko_message_to_response2(ret, code, msg):
    ret['response'] = ''
    ret['err_code'] = code
    ret['err_msg']  = msg
