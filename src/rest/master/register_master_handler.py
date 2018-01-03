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
import rest.booking.booking_constant as BC
from sqlalchemy import func
from data.session.mysql_session import engine, Session
from data.model.data_model import Master, MasterTimeSlot, MasterPreferedArea, MasterAccount
from response import Response
from response import add_err_message_to_response
from err.error_handler import print_err_detail, err_dict
from cron.master_schedule_date_builder import ScheduleBuilder

try:
    from utils.secrets import __UPLOADS__, IMG_SERVER
except ImportError:
    __UPLOADS__ = '/home/'
    IMG_SERVER = 'localhost'


class RegisterMasterHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')

        name            = self.get_argument('name', '')
        age             = self.get_argument('age', '')
        cardinal        = self.get_argument('cardinal', 0)
        gender          = self.get_argument('gender', 1)
        phone           = self.get_argument('phone', '')
        address         = self.get_argument('address', '')
        device          = self.get_argument('device', '')
        bank_name       = self.get_argument('bank_name', '')
        account_no      = self.get_argument('account_no', '')
        work_date       = self.get_argument('work_date', '')
        another_job     = self.get_argument('another_job', 0)
        need_route      = self.get_argument('need_route', 0)
        alergy          = self.get_argument('alergy', 0)
        t_size          = self.get_argument('t_size', 'M')
        feedback        = self.get_argument('feedback', '')
        message         = self.get_argument('message', '')
        start_hours     = self.get_argument('start_hours', '')
        end_hours       = self.get_argument('end_hours', '')
        region_ids      = self.get_argument('region_ids', '')

        # convert type
        age         = int(age)
        gender      = int(gender)
        cardinal    = int(cardinal)
        another_job = int(another_job)
        need_route = int(need_route)
        alergy = int(alergy)

        if work_date == '':
            work_date = dt.datetime.now() + dt.timedelta(days=1)
            
        work_date = dt.datetime.strptime(work_date, '%Y%m%d')

        phone       = phone.replace('-', '')
        account_no  = account_no.replace('-', '')

        print name, age, gender, cardinal
        print phone, address, device
        print bank_name, account_no
        print work_date
        print another_job, need_route, alergy, t_size
        print feedback, message
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
            new_master = Master(id = master_id,
                                manager_id = 'd55f6e50-7cca-4c52-ab78-3747385386ef',
                                name = name,
                                level = 1,
                                cardinal = cardinal,
                                age = age,
                                gender = gender,
                                img_url = img_url,
                                phone = phone,
                                address = address,
                                pet_alergy = alergy,
                                need_route = need_route,
                                another_job = another_job,
                                t_size = t_size,
                                feedback = feedback,
                                message = message,
                                active = 1,
                                dateofreg = dt.datetime.now())

            # add account
            bank_dict = BC.bank_dict
            account = MasterAccount(master_id = master_id, account_no = account_no,
                                    bank_code = bank_dict[bank_name], bank_name = bank_name,
                                    datetime = dt.datetime.now())
            session.add(account)

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
            schedule_builder.add_new_master_schedule_from_start_date(master_id, work_date)

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
