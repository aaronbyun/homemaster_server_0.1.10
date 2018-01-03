#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')


import json
import requests
from err.error_handler import print_err_detail, err_dict

try:
    from utils.secrets import JANDI_ON
except ImportError:
    JANDI_ON = False

jandi_urls = {}
jandi_urls['NEW_BOOKING']           = 'https://wh.jandi.com/connect-api/webhook/11415021/de317f9b090e8423b96c8054a4529714'
jandi_urls['HOMEMASTER_REST']       = 'https://wh.jandi.com/connect-api/webhook/11415021/fbf1a91ef5d0ba137b88484d4e210ff9'
jandi_urls['APPLY_HOMEMASTER']      = 'https://wh.jandi.com/connect-api/webhook/11415021/85c004434077f9fa21fbac50a8a5ea93'
jandi_urls['MOVING_IN_CLEANING']    = 'https://wh.jandi.com/connect-api/webhook/11415021/3da6fb6a42460f6d38be79204b776d9f'
jandi_urls['OFFICE_CLEANING']       = 'https://wh.jandi.com/connect-api/webhook/11415021/793e9cee3bc3a5908604e33c3c8704d6'
jandi_urls['NEW_WEB']               = 'https://wh.jandi.com/connect-api/webhook/11415021/6aab78343e84e4b881f8ec133b4eae99'
jandi_urls['BOOKING_NOT_AVAILABE']  = 'https://wh.jandi.com/connect-api/webhook/11415021/13497444d17664b4db1e674ab58a4d11'
jandi_urls['11ST_BOOKING']          = 'https://wh.jandi.com/connect-api/webhook/11415021/2ceb9ffc1363b467dadce11aff8b527f'


def send_jandi(channel_name, body, title, description, color = '#FAC11B'):
    try:
        print JANDI_ON
        if not JANDI_ON:
            return

        if channel_name in jandi_urls:
            jandi_url = jandi_urls[channel_name]
        else:
            jandi_url = 'https://wh.jandi.com/connect-api/webhook/11415021/de317f9b090e8423b96c8054a4529714'

        headers = {'Accept': 'application/vnd.tosslab.jandi-v2+json', 'Content-Type' : 'application/json'}
        data = {"body" : body,
                "connectColor" : color,
                "connectInfo" : [
                    {"title" : title,
                    "description" : description
                    }]
                }

        response = requests.post(jandi_url, data = json.dumps(data), headers = headers)

    except Exception, e:
        print_err_detail(e)
