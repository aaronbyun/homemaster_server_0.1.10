#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import datetime as dt
from collections import OrderedDict


def convert_house_type_size(house_type, house_size):
    if house_type == 3:
        house_type = 0

    if house_type == 0: # officetel
        house_type = 'officetel'
        if house_size <= 12:
            house_size = 12
        elif house_size <= 20:
            house_size = 20
        elif house_size <= 30:
            house_size = 30
        elif house_size <= 40:
            house_size = 40
        else:
            house_size = 54

    elif house_type == 1: # house
        house_type = 'rowhouse'
        if house_size <= 7:
            house_size = 7
        elif house_size <= 13:
            house_size = 13
        elif house_size <= 19:
            house_size = 19
        elif house_size <= 29:
            house_size = 29
        elif house_size <= 39:
            house_size = 39
        else:
            house_size = 54

    elif house_type == 2: # apartment
        house_type = 'apartment'
        if house_size <= 24:
            house_size = 24
        elif house_size <= 34:
            house_size = 34
        elif house_size <= 44:
            house_size = 44
        else:
            house_size = 54

    return house_type, house_size


def get_additional_tasks_and_prices(additional_task, house_type, house_size):
    tasks_prices = OrderedDict()

    tasks = ['vacuum', 'fridge_2', 'fridge_1', 'cloth_1', 'laundry', 'balconi', 'window']
    kor_tasks = ['', '양문형냉장고', '단문형냉장고', '옷장정리', '빨래', '베란다', '창문,창틀']
    bits = "{0:07b}".format(additional_task)

    for i in xrange(5, -1, -1):
        if bits[i+1] == '1':
            if i+1 == 6: # 창문일 경우
                house_type, house_size = convert_house_type_size(house_type, house_size)
                key = '%s_%s' % (house_type, house_size)
                value = additional_task_time_price_dict[tasks[i+1]][key]

                tasks_prices['창문,창틀'] = value['price']
            else: #나머지
                value = additional_task_time_price_dict[tasks[i+1]]
                tasks_prices[kor_tasks[i+1]] = value['price']

    return tasks_prices



def get_time_price(appointment_type, house_type, house_size):
    house_type, house_size = convert_house_type_size(house_type, house_size)

    if appointment_type == 3:
        appointment_type = 0

    key = '%s_%d' % (house_type, house_size)
    print key
    val = cleaning_time_price_dict[key][appointment_type]

    tp_key = '%s_%s' % (key, appointment_type)

    return tp_key, val['time'], val['price'], 0


def get_additional_task_time_price(additional_task, house_type, house_size):
    tasks = ['vacuum', 'fridge_2', 'fridge_1', 'cloth_1', 'laundry', 'balconi', 'window']
    bits = "{0:07b}".format(additional_task)

    total_time = 0
    total_price = 0

    for i in xrange(6):
        if bits[i+1] == '1':
            if i+1 == 6: # 창문일 경우
                house_type, house_size = convert_house_type_size(house_type, house_size)
                key = '%s_%s' % (house_type, house_size)
                value = additional_task_time_price_dict[tasks[i+1]][key]
                total_time += value['time']
                total_price += value['price']
            else: #나머지
                value = additional_task_time_price_dict[tasks[i+1]]
                total_time += value['time']
                total_price += value['price']

    return total_time, total_price

def get_basic_time_price(house_type, house_size):
    house_type, house_size = convert_house_type_size(house_type, house_size)
    key = '%s_%s' % (house_type, house_size)
    time_price_list = cleaning_time_price_dict[key]

    return time_price_list

def get_window_time_price(house_type, house_size):
    house_type, house_size = convert_house_type_size(house_type, house_size)
    key = '%s_%s' % (house_type, house_size)
    value = additional_task_time_price_dict['window'][key]

    return value['price'], value['time']

def convert_basic_time_price_for_app():
    basic_time_price_names = ['officetel_12', 'officetel_20', 'officetel_30', 'officetel_40', 'officetel_54', 'officetel_54',
                              'rowhouse_7'  , 'rowhouse_13',  'rowhouse_19' , 'rowhouse_29',  'rowhouse_39',  'rowhouse_54', 'rowhouse_54',
                              'apartment_24', 'apartment_34', 'apartment_44', 'apartment_54', 'apartment_54']
    converted_price = []
    converted_time  = []
    basic_time  = []

    name_index = 0

    for basic_time_price_name in basic_time_price_names:
        info_list = cleaning_time_price_dict[basic_time_price_name]

        index = 0
        basic_price = []

        for info in info_list:
            if index == 3:
                index += 1
                continue

            basic_price.append(info['price'])
            basic_time.append(info['time'] / 6)
            index += 1
        print 'name_index : ', name_index

        if name_index == 5 or name_index == 12 or name_index == 17:
            basic_time = set(basic_time)
            if name_index == 12:
                basic_time.remove(45)

            basic_time = list(basic_time)
            basic_time.sort()
            converted_time.append(basic_time)
            basic_time = []

        name_index += 1

        basic_price.sort()
        converted_price.append(basic_price)

    converted_time = [i for kind in converted_time for i in kind]

    return converted_price, converted_time




def hm_get_additional_task_time_price(org_price, org_time, org_additional_task, additional_task, house_type, house_size):
    tasks = ['vacuum', 'fridge_2', 'fridge_1', 'cloth_1', 'laundry', 'balconi', 'window']
    bits = "{0:07b}".format(additional_task)
    org_bits = "{0:07b}".format(org_additional_task)

    print "bits : ", bits
    print "org_bits : ", org_bits

    total_time = org_time
    total_price = org_price

    for i in xrange(6):
        if org_bits[i+1] == bits[i+1]:
            continue

        if i+1 == 6: # 창문일 경우
            house_type, house_size = convert_house_type_size(house_type, house_size)
            print "house_type : ", house_type
            print "house_size : ", house_size
            key = '%s_%s' % (house_type, house_size)
            value = additional_task_time_price_dict[tasks[i+1]][key]
            if org_bits[i+1] > bits[i+1]:
                total_time -= dt.timedelta(minutes = value['time'])
                total_price -= value['price']
            else:
                total_time += dt.timedelta(minutes = value['time'])
                total_price += value['price']

        else: #나머지
            value = additional_task_time_price_dict[tasks[i+1]]
            if org_bits[i+1] > bits[i+1]:
                total_time -= dt.timedelta(minutes = value['time'])
                total_price -= value['price']
            else:
                total_time += dt.timedelta(minutes = value['time'])
                total_price += value['price']

    return total_time, total_price

cleaning_time_price_dict = {
    'officetel_12' : [{'price' : 45000, 'time' : 180 },
                      {'price' : 42000, 'time' : 180 },
                      {'price' : 42000, 'time' : 180 },
                      {'price' : 45000, 'time' : 180 },
                      {'price' : 42000, 'time' : 180 }],

    'officetel_20' : [{'price' : 45000, 'time' : 180},
                      {'price' : 42000, 'time' : 180},
                      {'price' : 42000, 'time' : 180},
                      {'price' : 45000, 'time' : 180},
                      {'price' : 42000, 'time' : 180}],

    'officetel_30' : [{'price' : 45000, 'time' : 180},
                      {'price' : 42000, 'time' : 180},
                      {'price' : 42000, 'time' : 180},
                      {'price' : 45000, 'time' : 180},
                      {'price' : 42000, 'time' : 180}],

    'officetel_40' : [{'price' : 52500, 'time' : 210},
                      {'price' : 49000, 'time' : 210},
                      {'price' : 49000, 'time' : 210},
                      {'price' : 52500, 'time' : 210},
                      {'price' : 49000, 'time' : 210}],

    'officetel_54' : [{'price' : 60000, 'time' : 240},
                      {'price' : 55000, 'time' : 240},
                      {'price' : 55000, 'time' : 240},
                      {'price' : 60000, 'time' : 240},
                      {'price' : 55000, 'time' : 240}],

    # house
    'rowhouse_7' : [{'price' : 45000, 'time' : 180},
                    {'price' : 42000, 'time' : 180},
                    {'price' : 42000, 'time' : 180},
                    {'price' : 45000, 'time' : 180},
                    {'price' : 42000, 'time' : 180}],

    'rowhouse_13' : [{'price' : 45000, 'time' : 180},
                     {'price' : 42000, 'time' : 180},
                     {'price' : 42000, 'time' : 180},
                     {'price' : 45000, 'time' : 180},
                     {'price' : 42000, 'time' : 180}],

    'rowhouse_19' : [{'price' : 45000, 'time' : 180},
                     {'price' : 42000, 'time' : 180},
                     {'price' : 42000, 'time' : 180},
                     {'price' : 45000, 'time' : 180},
                     {'price' : 42000, 'time' : 180}],


    'rowhouse_29' : [{'price' : 52500, 'time' : 210},
                     {'price' : 49000, 'time' : 210},
                     {'price' : 49000, 'time' : 210},
                     {'price' : 52500, 'time' : 210},
                     {'price' : 49000, 'time' : 210}],


    'rowhouse_39' : [{'price' : 60000, 'time' : 240},
                     {'price' : 55000, 'time' : 240},
                     {'price' : 55000, 'time' : 240},
                     {'price' : 60000, 'time' : 240},
                     {'price' : 55000, 'time' : 240}],


    'rowhouse_54' : [{'price' : 75000, 'time' : 300},
                    {'price' : 70000, 'time' : 300},
                    {'price' : 70000, 'time' : 300},
                    {'price' : 75000, 'time' : 300},
                    {'price' : 70000, 'time' : 300}],
    # apartment
    'apartment_24' : [{'price' : 52500, 'time' : 210},
                     {'price' : 49000, 'time' : 210},
                     {'price' : 49000, 'time' : 210},
                     {'price' : 52500, 'time' : 210},
                     {'price' : 49000, 'time' : 210}],


    'apartment_34' : [{'price' : 60000, 'time' : 240},
                     {'price' : 55000, 'time' : 240},
                     {'price' : 55000, 'time' : 240},
                     {'price' : 60000, 'time' : 240},
                     {'price' : 55000, 'time' : 240}],


    'apartment_44' : [{'price' : 67500, 'time' : 270},
                      {'price' : 63000, 'time' : 270},
                      {'price' : 63000, 'time' : 270},
                      {'price' : 67500, 'time' : 270},
                      {'price' : 63000, 'time' : 270}],


    'apartment_54' : [{'price' : 75000, 'time' : 300},
                     {'price' : 70000, 'time' : 300},
                     {'price' : 70000, 'time' : 300},
                     {'price' : 75000, 'time' : 300},
                     {'price' : 70000, 'time' : 300}]
}

additional_task_time_price_dict = {
    'window' : {
         'officetel_12' : {'price' : 15000, 'time' : 60},
         'officetel_20' : {'price' : 15000, 'time' : 60},
         'officetel_30' : {'price' : 30000, 'time' : 120},
         'officetel_40' : {'price' : 45000, 'time' : 180},
         'officetel_54' : {'price' : 60000, 'time' : 240},

         'rowhouse_7'  : {'price' : 15000, 'time' : 60},
         'rowhouse_13' : {'price' : 30000, 'time' : 120},
         'rowhouse_19' : {'price' : 45000, 'time' : 180},
         'rowhouse_29' : {'price' : 52500, 'time' : 210},
         'rowhouse_39' : {'price' : 60000, 'time' : 240},
         'rowhouse_54' : {'price' : 75000, 'time' : 300},

         'apartment_24' : {'price' : 37500, 'time' : 150},
         'apartment_34' : {'price' : 52500, 'time' : 210},
         'apartment_44' : {'price' : 60000, 'time' : 240},
         'apartment_54' : {'price' : 75000, 'time' : 300}
    },

    'fridge_1' : {'price' : 30000, 'time' : 120},
    'fridge_2' : {'price' : 45000, 'time' : 180},

    'cloth_1'  : {'price' : 15000, 'time' : 60},
    'cloth_2'  : {'price' : 30000, 'time' : 120},
    'cloth_3'  : {'price' : 45000, 'time' : 180},

    'laundry' : {'price' : 0, 'time' : 0},

    'balconi'  : {'price' : 15000, 'time' : 60}
}


if __name__ == '__main__':
    for k, v in get_additional_tasks_and_prices(58, 0, 20).items():
        print k, v

    print get_additional_task_time_price(11, 0, 20)
    print get_additional_task_time_price(12, 0, 20)
    print get_additional_task_time_price(16, 0, 20)
