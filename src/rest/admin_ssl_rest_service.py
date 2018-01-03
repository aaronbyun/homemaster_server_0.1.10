#-*- coding: utf-8 -*-

import tornado.ioloop
import tornado.web
import tornado.httpserver
from admin_register_api import application

try:
    from utils.secrets import CERTFILE_PATH, KEYFILE_PATH
except ImportError:
    CERTFILE_PATH = ''
    KEYFILE_PATH = ''

if __name__ == "__main__":
    print 'Starting server on port 9443'

    http_server = tornado.httpserver.HTTPServer(application, ssl_options={
        'certfile' : CERTFILE_PATH,
        'keyfile' : KEYFILE_PATH
    })

    http_server.listen(9443)
    tornado.ioloop.IOLoop.instance().start()
