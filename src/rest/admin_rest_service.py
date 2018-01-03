#-*- coding: utf-8 -*-

import tornado.ioloop
import tornado.web
import tornado.httpserver
from admin_register_api import application

if __name__ == "__main__":
    print 'Starting server on port 8998'

    application.listen(8998)
    #server = tornado.httpserver.HTTPServer(application)
    #server.bind(8888)
    #server.start(4)
    tornado.ioloop.IOLoop.instance().start()
    #tornado.ioloop.IOLoop.current().start()
