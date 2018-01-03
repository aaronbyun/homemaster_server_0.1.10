#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import json
import requests
import base64

try:
    from utils.secrets import MAIN_CALL, BLUEHOUSE_ID, BLUEHOUSE_KEY
except ImportError:
    MAIN_CALL = '18000199'
    BLUEHOUSE_ID = 'homemaster_server2'
    BLUEHOUSE_KEY = '992ade82d7d411e6a9f70cc47a1fcfae'



class MessageSender(object):
    url = "https://api.bluehouselab.com/smscenter/v1.0/sendlms"

    def __init__(self):
        appid = BLUEHOUSE_ID
        apikey = BLUEHOUSE_KEY
        credential = "Basic "+base64.encodestring(appid+':'+apikey).strip()

        self.headers = {
            "Content-type": "application/json;charset=utf-8",
            "Authorization": credential,
        }

    def send(self, receivers, subject, content):
        value = {
            'sender' : MAIN_CALL,
            'receivers' : receivers,
            'subject' : subject,
            'content' : content
        }

        data = json.dumps(value, ensure_ascii=False).encode('utf-8')

        response = requests.post(MessageSender.url, data=data, headers = self.headers)
        print response.status_code
        print response.text

if __name__ == '__main__':
    message_sender = MessageSender()
    message_sender.send(['01034576360'], '이것은 제목이다', '이것은 내용이다. 이것은 존나게 긴 내용이다. 이것은 완전 허를 내두를 정도로 긴내용이다. 이것은 갈 수 없다. 이것은 전송 된다. 하하하하하')
