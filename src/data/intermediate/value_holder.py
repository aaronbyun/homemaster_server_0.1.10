#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import redis
import pickle
import datetime as dt


try:
    from utils.secrets import REDIS_HOST, REDIS_PORT, REDIS_PWD
except ImportError:
    REDIS_HOST = 'localhost'
    REDIS_PORT = 6379
    REDIS_PWD = ''


TIMEOUT = 600 # 10 minutes
TIMEOUT_11ST = 600 * 9# 10 minutes * 6 * 1.5
#TIMEOUT = 10 # 8 minutes

class IntermediateValueHolder(object):
    def __init__(self):
        self.r = redis.Redis(host = REDIS_HOST, port = REDIS_PORT, password = REDIS_PWD)

    def store(self, key, obj, source = 'hm'):
        pickled_obj = pickle.dumps(obj)
        if self.r.setnx(key, pickled_obj):
            if source == 'hm':
                self.r.expire(key, TIMEOUT)
            else:
                self.r.expire(key, TIMEOUT_11ST)
            return True

        return False

    def retrieve(self, key):
        data = self.r.get(key)
        if data == None:
            return None

        unpickled_obj = pickle.loads(data)
        return unpickled_obj

    def store_all(self, keys, objs):
        dictionary = dict(zip(keys, pickle.dumps(objs)))
        if self.r.msetnx(dictionary):
            for k in keys:
                self.r.expire(k, TIMEOUT)

            return True

        return False

    def store_keys(self, keys, source = 'hm'):
        dictionary = dict(zip(keys, keys))
        if self.r.msetnx(dictionary):
            for k in keys:
                if source == 'hm':
                    self.r.expire(k, TIMEOUT)
                else:
                    self.r.expire(k, TIMEOUT_11ST)

            return True

        return False

    def retrieve_all(self, keys):
        data = self.r.mget(keys)
        return [pickle.loads(d) if d != None else None for d in data]

    def exists(self, key):
        return self.r.exists(key)

    def remove(self, key):
        self.r.delete(key)



if __name__ == '__main__':
    '''r = redis.Redis(host = REDIS_HOST, port = REDIS_PORT, password = REDIS_PWD)

    obj = [{'master_id' : '12334', 'date' : '20150925', 'start_time' : dt.time(9), 'end_time' : dt.time(10)},
            {'master_id' : '12334', 'date' : '20151003', 'start_time' : dt.time(9), 'end_time' : dt.time(10)},
            {'master_id' : '12334', 'date' : '20151010', 'start_time' : dt.time(9), 'end_time' : dt.time(10)},
            {'master_id' : '12334', 'date' : '20151017', 'start_time' : dt.time(9), 'end_time' : dt.time(10)}]


    pickled_obj = pickle.dumps(obj)
    r.set('test', pickled_obj)
    unpickled_obj = pickle.loads(r.get('test'))

    print obj
    print pickled_obj
    print unpickled_obj
    print obj == unpickled_obj'''

    holder = IntermediateValueHolder()
    holder.store_keys(['da2a1f50-fd36-40bf-8460-55b3e1b2c459_20160607', 'da2a1f50-fd36-40bf-8460-55b3e1b2c459_20160621'])
    print holder.exists('da2a1f50-fd36-40bf-8460-55b3e1b2c459_20160607')
