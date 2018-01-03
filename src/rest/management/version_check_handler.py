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
from data.model.data_model import Version, MasterVersion, IOSVersion
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from err.error_handler import print_err_detail, err_dict
from sqlalchemy import func, desc, or_, and_
from response import Response
from response import add_err_message_to_response

class VersionHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        version = self.get_argument('version', '')
        apptype = self.get_argument('apptype', 'user')
        ostype  = self.get_argument('ostype', '')

        if ostype == '':
            ostype = 'android'

        ret = {}

        splited_version = version.split('.')
        major = splited_version[0]
        minor = splited_version[1]
        patch = splited_version[2]

        print major, minor, patch

        try:
            session = Session()

            description = ''

            if apptype == 'user':
                if ostype == 'android':
                    current_version = session.query(Version) \
                                            .order_by(desc(Version.major), desc(Version.minor), desc(Version.patch)) \
                                            .first()

                    description = current_version.description
                    index = session.query(Version.id) \
                            .filter(Version.major == major) \
                            .filter(Version.minor == minor) \
                            .filter(Version.patch == patch) \
                            .first()

                    if index == None:
                        index = 9999999 # big number
                    else:
                        index = index[0]

                    mandatories = session.query(Version) \
                                    .filter(Version.id > index) \
                                    .all()
                else:
                    current_version = session.query(IOSVersion) \
                                            .order_by(desc(IOSVersion.major), desc(IOSVersion.minor), desc(IOSVersion.patch)) \
                                            .first()

                    description = current_version.description
                    index = session.query(IOSVersion.id) \
                            .filter(IOSVersion.major == major) \
                            .filter(IOSVersion.minor == minor) \
                            .filter(IOSVersion.patch == patch) \
                            .first()

                    if index == None:
                        index = 9999999 # big number
                    else:
                        index = index[0]

                    mandatories = session.query(IOSVersion) \
                                    .filter(IOSVersion.id > index) \
                                    .all()

            elif apptype == 'master':
                current_version = session.query(MasterVersion) \
                                        .order_by(desc(MasterVersion.major), desc(MasterVersion.minor), desc(MasterVersion.patch)) \
                                        .first()

                description = current_version.description
                index = session.query(MasterVersion.id) \
                        .filter(MasterVersion.major == major) \
                        .filter(MasterVersion.minor == minor) \
                        .filter(MasterVersion.patch == patch) \
                        .first()

                if index == None:
                    index = 9999999 # big number
                else:
                    index = index[0]

                mandatories = session.query(MasterVersion) \
                                .filter(MasterVersion.id > index) \
                                .all()

            else:
                mandatories = []
                current_version = '0.0.0'

            mandatory = 0
            for m in mandatories:
                # print m.id
                if m.mandatory == 1:
                    mandatory = 1
                    break

            ret['response'] = {'mandatory' : mandatory, 'description' : description}
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()

            self.write(json.dumps(ret))         