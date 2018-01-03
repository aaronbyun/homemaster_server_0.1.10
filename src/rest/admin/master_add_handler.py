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
from sqlalchemy import func
from data.session.mysql_session import engine, Session
from data.model.data_model import Master, MasterTimeSlot, MasterPreferedArea
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from cron.master_schedule_date_builder import ScheduleBuilder

try:
    from utils.secrets import __UPLOADS__, IMG_SERVER
except ImportError:
    __UPLOADS__ = '/home/'
    IMG_SERVER = 'localhost'


class MasterAddHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")

        #name:홈마이름, age:나이, phone:홈마폰, address:주소, manager_name:담당매니저, manager_phone:매니저폰, cardinal:홈마의 기수
        name            = self.get_argument('name', '')
        age             = self.get_argument('age', '')
        gender          = self.get_argument('gender', 2)
        address         = self.get_argument('address', '')
        phone           = self.get_argument('phone', '')
        manager_id      = self.get_argument('manager_id', '')
        level           = self.get_argument('level', 0)
        cardinal        = self.get_argument('cardinal', 0)

        start_hours     = self.get_argument('start_hours', '')
        end_hours       = self.get_argument('end_hours', '')
        region_ids      = self.get_argument('region_ids', '')          

        # convert type
        age         = int(age)
        gender      = int(gender)
        level       = int(level)
        cardinal    = int(cardinal)

        print start_hours
        print end_hours
        print region_ids
        
        start_hours = start_hours.split(',')
        end_hours   = end_hours.split(',')
        region_ids  = region_ids.split(',')

        ret = {}

        try:
            session = Session()

            # master info
            master_id = str(uuid.uuid4())

            img_url = '%s/images/%s.%s' % (IMG_SERVER, phone, 'png')
            new_master = Master(id = master_id, manager_id = manager_id, name = name, age = age, gender = gender,
                                img_url = img_url, address = address, phone = phone, level = level, cardinal = cardinal, dateofreg = dt.datetime.now())

            # master time slot
            for i in xrange(7):
                sh = start_hours[i]
                eh = end_hours[i]

                if sh == '' or eh == '': continue

                sh = int(sh)
                eh = int(eh)

                new_master_region = MasterTimeSlot(master_id = master_id, day_of_week = i, start_time = dt.time(sh), end_time = dt.time(eh))
                session.add(new_master_region)

            for rid in region_ids:
                rid = int(rid)

                new_master_area = MasterPreferedArea(master_id = master_id, prefered_gu = rid)
                session.add(new_master_area)

            session.add(new_master)
            session.commit()

            schedule_builder = ScheduleBuilder()
            schedule_builder.add_new_master_schedule(master_id)

            # 사진 등록
            '''fileinfo = self.request.files['filearg'][0]
            print "fileinfo is", fileinfo
            fname = fileinfo['filename']
            extn = os.path.splitext(fname)[1]
            cname = master_id + extn
            fh = open(__UPLOADS__ + cname, 'w')
            fh.write(fileinfo['body'])
            print cname + " is uploaded!! Check %s folder" %__UPLOADS__'''

            ret['response'] = Response.SUCCESS
            self.set_status(Response.RESULT_OK)

        except Exception, e:
            session.rollback()

            print_err_detail(e)
            self.set_status(Response.RESULT_SERVERERROR)
            add_err_message_to_response(ret, err_dict['err_mysql'])

        finally:
            session.close()
            self.write(json.dumps(ret))
