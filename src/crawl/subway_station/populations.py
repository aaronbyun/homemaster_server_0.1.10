#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import requests
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support import ui as ui

class PopulationNearMetro(object):
    def __init__(self):
        chromedriver = '/Users/aaronbyun/development/Libs/chromedriver'
        os.environ['webdriver.chrome.driver'] = chromedriver
        self.driver = webdriver.Chrome(chromedriver)

    def number_of_household_in_danji(self, danji_url):
        self.driver.get(danji_url)
        response = self.driver.page_source
        soup = BeautifulSoup(response, 'lxml')

        try:
            household = soup.find_all('em', attrs = {'class' : 'fc_gray'})[0]
            household = household.get_text(strip = True)
        except Exception, e:
            return 0

        return int(household.replace(',', ''))


    def number_of_household(self, metro_code):
        url = 'http://realestate.daum.net/maemul/subway/%s/A1A3A4/*/maemullist' % metro_code
        #res = requests.get(url)
        self.driver.get(url)
        response = self.driver.page_source
 
        soup = BeautifulSoup(response, 'lxml')

        household_num = 0
        danji_list = soup.find('ul', attrs = {'class' : 'list_estateinfo list_estateinfo2'})
        try:
            danji_list = danji_list.find_all('a', attrs = {'class' : 'link_menu'})
        except Exception, e:
            return 0
        
        for danji in danji_list:
            link = 'http://realestate.daum.net' + danji['href']
            danji_household_num = self.number_of_household_in_danji(link)
            household_num += danji_household_num

        return household_num

    def dispose():
        self.driver.quit()


if __name__ == '__main__':
    population = PopulationNearMetro()

    city_metro_dict = {''' '과천시' : ['SES1454', 'SES1453', 'SES1452', 'SES1451', 'SES1450'], 
             '화성시' : ['SES1716'], 
             '남양주시' : ['SES5019', 'SES5003', 'SES5004', 'SES5005', 'SES5006', 'SES5007', 'SES1206', 'SES1207', 'SES1208', 'SES1209', 'SES1210', 'SES1211'], 
             '수원시 영통구' : ['SES1867', 'SES1868', 'SES1869', 'SES1870', 'SES3411', 'SES3412'], 
             '수원시 권선구' : ['SES1715'], 
             '수원시 장안구' : ['SES1711'], 
             '수원시 팔달구' : ['SES1712', 'SES1713'], 
             '안양시 동안구' : ['SES1457', 'SES1456', 'SES1455'], 
             '안양시 만안구' : ['SES1707', 'SES1706', 'SES1705', 'SES1704'], 
             '용인시 기흥구' : ['SES1866', 'SES1865', 'SES1864', 'SES1863', 'SES1862', 'SES1861', 'SES3702', 'SES3703', 'SES3704', 'SES3705', 'SES3706'], 
             '용인시 처인구' : ['SES3707', 'SES3708', 'SES3709', 'SES3710', 'SES3711', 'SES3712', 'SES3713', 'SES3714', 'SES3715', 'SES3716'], 
             '용인시 수지구' : ['SES3410', 'SES3409', 'SES3408', 'SES3407'], 
             '일산' : ['SES1955', 'SES1956', 'SES1957', 'SES1958', 'SES4010', 'SES4009', 'SES4008', 'SES4007'],
             '인천' : ['SES3145', 'SES3144', 'SES3143', 'SES3142', 'SES3141', 'SES3140', 'SES3132', 'SES3131',
                      'SES3130', 'SES3129', 'SES3128', 'SES3127', 'SES3126', 'SES3125', 'SES3124', 'SES3123', 
                      'SES3122', 'SES3121', 'SES3120', 'SES3119', 'SES3118', 'SES3117', 'SES3116', 'SES3115', 
                      'SES3114', 'SES3113', 'SES3112', 'SES3111', 'SES3110', 'SES3504', 'SES3505', 'SES3506',
                      'SES3507', 'SES3508', 'SES3509', 'SES3510', 'SES3511', 'SES3512', 'SES3513', 'SES3514', 
                      'SES1811', 'SES1817', 'SES1810', 'SES1823', 'SES1809', 'SES1816', 'SES1808', 'SES1807', 
                      'SES1806', 'SES1815'],'''
            '부산' : ['PSS101', 'PSS102', 'PSS103', 'PSS104', 'PSS105', 'PSS106', 'PSS107', 'PSS108', 'PSS109', 'PSS110', 'PSS111', 'PSS112',
                    'PSS113', 'PSS114', 'PSS115', 'PSS116', 'PSS117', 'PSS118', 'PSS119', 'PSS120', 'PSS121', 'PSS122', 'PSS123', 'PSS124', 
                    'PSS125', 'PSS126', 'PSS127', 'PSS128', 'PSS129', 'PSS130', 'PSS131', 'PSS132', 'PSS133', 'PSS134', 'PSS135', 
                    'PSS201', 'PSS202', 'PSS203', 'PSS204', 'PSS205', 'PSS206', 'PSS207', 'PSS208', 'PSS209', 'PSS210', 'PSS211', 'PSS212',
                    'PSS213', 'PSS214', 'PSS215', 'PSS216', 'PSS217', 'PSS218', 'PSS219', 'PSS220', 'PSS221', 'PSS222', 'PSS223', 'PSS224',
                    'PSS301', 'PSS302', 'PSS303', 'PSS304', 'PSS305', 'PSS306', 'PSS307', 'PSS308', 'PSS309', 'PSS310', 'PSS311', 'PSS312',
                    'PSS313', 'PSS314', 'PSS315', 'PSS316', 'PSS317', 'PSS318', 'PSS319', 'PSS320', 'PSS321', 'PSS322', 'PSS323', 'PSS324', 
                    'PSS401', 'PSS402', 'PSS403', 'PSS404', 'PSS405', 'PSS406', 'PSS407', 'PSS408', 'PSS409', 'PSS410', 'PSS411', 'PSS412',
                    'PSS413', 'PSS414', 'PSS415', 'PSS416', 'PSS417', 'PSS418', 'PSS419', 'PSS420', 'PSS421', 'PSS422', 'PSS423', 'PSS424', 
                    'PSS1001', 'PSS1002', 'PSS1003', 'PSS1004', 'PSS1005', 'PSS1006', 'PSS1007', 'PSS1008', 'PSS1009', 'PSS1010', 'PSS1011', 'PSS112',
                    'PSS1013', 'PSS1014', 'PSS1015', 'PSS1016', 'PSS1017', 'PSS1018', 'PSS1019', 'PSS1020', 'PSS1021', 'PSS1022', 'PSS1023', 'PSS1024']
             }
    for city in city_metro_dict:
        print city
        cnt = 0
        for m in city_metro_dict[city]:
            number_of_household = population.number_of_household(m)
            cnt += number_of_household
            print m, number_of_household

        print cnt