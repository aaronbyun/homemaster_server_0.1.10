#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import geocoder
import geohash
import googlemaps
import re
import math
import datetime as dt

from err.error_handler import print_err_detail, err_dict

try:
    from utils.secrets import GOOGLE_API_KEY
except ImportError:
    GOOGLE_API_KEY = ''


def remove_parentheses(address):
    try:
        p = re.compile(r'\([^)]*\)')
        return re.sub(p, '', address)
    except Exception, e:
        print_err_detail(e)
        return address


def get_latlng_from_address(address):
    try:
        print "function remove_parentheses start : ", address
        address = remove_parentheses(address)
        print "function remove_parentheses end : ", address
        g = geocoder.google(address)
        print "geocoder.google(address) end : ", g
        if g.latlng:
            return g.latlng
        else:
            return [37.5609447,126.9795475]
    except Exception ,e:
        print_err_detail(e)
        return [37.5609447,126.9795475]


def get_geohash(latitude, longitude, precision):
    try:
        return geohash.encode(latitude, longitude, precision = precision)
    except Exception , e:
        print_err_detail(e)
        return ''

def get_moving_time(geohash1, geohash2):
    try:
        if geohash1 == None or geohash2 == None: # 바로 나오는 경우, 들어가는 경우
            return 0

        if geohash1 == '' or geohash2 == '': # 모를 경우에는 1시간을 줌
            return 60

        geohash1_parent = geohash1[:5]
        geohash2_parent = geohash2[:5]

        expanded = geohash.expand(geohash1_parent)
        expanded_depth2 = set()

        for gh in expanded:
            neighbors = geohash.neighbors(gh)
            expanded_depth2 = expanded_depth2.union(neighbors)

        expanded_depth2 = list(expanded_depth2)

        if geohash1 == geohash2:
            return 30

        elif geohash2_parent in expanded:
            return 60

        elif geohash2_parent in expanded_depth2:
            return 90
        else:
            return 120
    except Exception, e:
        print_err_detail(e)
        return 60


def get_moving_time_by_geo(latlng1, latlng2, time = dt.datetime.now()):
    try:
        gmaps = googlemaps.Client(key = GOOGLE_API_KEY)
        result = gmaps.distance_matrix(latlng1, latlng2, language='ko', units='metric', mode='transit', departure_time=time)

        rows = result['rows']
        if len(rows) == 0:
            return 60

        elements = rows[0]['elements'][0]
        if elements['status'] != 'OK':
            return 60

        mins = int(math.ceil(elements['duration']['value'] / 60.0))
        mins = int(mins / 30 + 1) * 30
        return mins

    except Exception, e:
        print_err_detail(e)


def get_moving_time_by_geos(origin, destinations, time = dt.datetime.now()):
    try:
        gmaps = googlemaps.Client(key = GOOGLE_API_KEY)
        result = gmaps.distance_matrix(origin, destinations, language='ko', units='metric', mode='transit', departure_time=time)

        print result

        rows = result['rows']
        if len(rows) == 0:
            raise Exception('0 results')

        if result['status'] != 'OK':
            raise Exception('status not OK')

        taking_times = []

        for dest in rows[0]['elements']:
            if dest['status'] == 'OK':
                mins = int(math.ceil(dest['duration']['value'] / 60.0))
                mins = int(mins / 30 + 1) * 30
            else:
                mins = 60

            taking_times.append(mins)

        return taking_times
    except Exception, e:
        print_err_detail(e)
        return []


def get_moving_time_by_address(address1, address2, time = dt.datetime.now()):
    try:
        gmaps = googlemaps.Client(key = GOOGLE_API_KEY)
        result = gmaps.distance_matrix(address1, address2, language='ko', units='metric', mode='transit', departure_time=time)

        row = result['rows']
        if len(row) <= 0:
            return 60

        element = row[0]['elements'][0]
        if element['status'] != 'OK':
            return 60

        mins = int(math.ceil(element['duration']['value'] / 60.0))
        mins = int(mins / 30 + 1) * 30
        return mins

    except Exception, e:
        print_err_detail(e)
        return 60


if __name__ == '__main__':
    #https://maps.googleapis.com/maps/api/distancematrix/json?origins=37.478265,126.983711&destinations=37.483156,126.946082&mode=transit&language=ko&key=AIzaSyDHOTMidsox5EPSsnFhvIb5Sfw_4wBM9fA
    #latlng1 = {'lat' : 37.478265, 'lng' : 126.983711}
    #latlng2 = [{'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.483156, 'lng' : 126.946082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.483156, 'lng' : 126.946082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}, {'lat' : 37.583256, 'lng' : 126.956082}]
    #print len(latlng2)
    #print get_moving_time_by_geos(latlng1, latlng2)
    #print get_moving_time_by_address('서운로 6', '서운로9길 18')

    print get_latlng_from_address('서울특별시 서초구 서운로 6  7층')

    '''print get_moving_time('wydmk7', 'wydmk7')
    print get_moving_time('wydmk7', 'wydmke')
    print get_moving_time('wydmk7', 'wydmm5')
    print get_moving_time('wydmk7', 'wydmj7')
    print get_moving_time('wydmk7', 'wydm6h')
'''
