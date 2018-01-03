#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')

import codecs
import argparse
import glob
from mysql.connector import connection
from mysql.connector import errorcode
from datetime import datetime

class BuildingAddressManager(object):
    def __init__(self):
        DB_ID = 'dev'
        DB_PWD = 'devhomemaster'
        DB_HOST = '210.183.239.45'
        DB_NAME = 'homemaster'

        self.conn = connection.MySQLConnection(user=DB_ID, password=DB_PWD, host=DB_HOST, database=DB_NAME)
        self.DORO_BUILDING_NO = 16
        self.DORO_MODIFICATION_CODE_INDEX = 22

        self.MODIFICATION_CODE_INSERT = '31'
        self.MODIFICATION_CODE_UPDATE = '34'
        self.MODIFICATION_CODE_DELETE = '63'

    def initiate(self, table, path):
        print 'Building Address Initiation Started...'

        query = "LOAD DATA LOCAL INFILE %s INTO TABLE " + table + " FIELDS TERMINATED BY '|' LINES TERMINATED BY '\n'"

        cursor = self.conn.cursor()

        for csv_file in glob.glob(path):
            cursor.execute(query, (csv_file, ))
            self.conn.commit()
            print csv_file, 'was imported...'
        cursor.close()

        print 'Initiation finished', datetime.now()

    def update_doro(self, path):
        pass

    def update_related_jibun(self, path):
        pass




if __name__ == '__main__':
    '''parser = argparse.ArgumentParser(description='Import Korean Address Data')
    parser.add_argument('--table', action='store', nargs='?', dest='table') # table is optional
    parser.add_argument('--pathreg', action='store', dest='path')
    parser.add_argument('--mode', action='store', dest='mode')

    args = parser.parse_args()

    table = args.table
    path = args.path
    mode = args.mode'''

    address_manager = BuildingAddressManager()

    '''if mode == 'initiate':
        address_manager.initiate(table, path)
    elif mode == 'update_doro':
        address_manager.update_doro(path)
    elif mode == 'update_jibun':
        address_manager.update_related_jibun(path)'''

    address_manager.initiate('doro_address', '/Users/aaronbyun/Downloads/address1508/building/*.txt')
    address_manager.initiate('jibun_address', '/Users/aaronbyun/Downloads/address1508/jibun/*.txt')
