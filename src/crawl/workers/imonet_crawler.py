# -*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import requests as req
import multiprocessing as mp
from pymongo import MongoClient
from bs4 import BeautifulSoup


NAME        = 1
BIRTH       = 2
GENDER      = 3
CHILDREN    = 4
CELLPHONE   = 5
PHONE       = 6
AVAIL_TIME  = 7
YEARS       = 9
CERTIFICATE = 10
SALARY      = 11
ADDRESS     = 15
BIO         = 16


def get_stripped_text(obj):
    return obj.get_text().strip()

def crawl_by_page(start, end):
    print 'crawler started', start, end
    mongo = mongo = MongoClient('127.0.0.1', 27017)
    db = mongo.worker
    db.authenticate('hmadmin', 'homemaster!@#$', source = 'worker')

    host = 'http://www.iiiiimo.net/Lesson/'

    page_url = host + 'teachList2.php?page={page}&id=&name=&mode=search&addr1=%BC%AD%BF%EF&lesson1=%B0%A1%BB%E7'
    session = req.Session()

    params = {'kjin' : 'kjinindex', 'id' : 'homemaster', 'passwd' : 'homema11', 'public' : 'student', 'x' : 38, 'y' : 11}
    res = session.post('https://www.iiiiimo.net:43431/login_tpree.php', data=params, verify=True)

    for i in xrange(end-start+1):
        page_num = start + i

        page_url = page_url.replace('{page}', str(page_num))
        crawl_urls = get_crawl_urls(page_url)

        for url in crawl_urls:
            res = session.get(host + url, cookies=session.cookies.get_dict())
            res.encoding = 'euc-kr'
            soup = BeautifulSoup(res.text)

            td_tags = soup.find_all(lambda tag: tag.name == 'td' and tag.has_attr('bgcolor') and tag['bgcolor'] == 'ffffff' and not tag.has_attr('height'))

            worker = {}

            worker['name']        = get_stripped_text(td_tags[NAME])
            worker['birth']       = get_stripped_text(td_tags[BIRTH]).replace(' 년생', '')
            worker['gender']      = get_stripped_text(td_tags[GENDER])
            worker['children']    = get_stripped_text(td_tags[CHILDREN])
            worker['cell']        = get_stripped_text(td_tags[CELLPHONE])
            worker['phone']       = get_stripped_text(td_tags[PHONE])
            worker['avail_time']  = get_stripped_text(td_tags[AVAIL_TIME])
            worker['years']       = get_stripped_text(td_tags[YEARS])
            worker['cert']        = get_stripped_text(td_tags[CERTIFICATE])
            worker['salary']      = get_stripped_text(td_tags[SALARY])
            worker['addr']        = get_stripped_text(td_tags[ADDRESS])
            worker['bio']         = get_stripped_text(td_tags[BIO])

            if db.meta.find_one({'name' : worker['name'], 'cell' : worker['cell']}) == None:
                print worker['name'], worker['birth'], worker['cell']
                db.meta.insert(worker)
            else:
                print 'already crawled...'

    mongo.close()


def get_crawl_urls(url):
    res = req.get(url)
    res.encoding = 'euc-kr'
    soup = BeautifulSoup(res.text)

    atags = soup.find_all(lambda tag: tag.name == 'a' and 'teachView.php' in tag['href'])
    crawl_urls = [a['href'] for a in atags]

    return crawl_urls


def run_crawl():
    num_proc = 20
    page_indexes = [(10*i+1, 10*(i+1)) for i in range(20)]
    procs = [mp.Process(target=crawl_by_page, args=(pi[0], pi[1])) for pi in page_indexes]

    for p in procs:
        p.start()

    for p in procs:
        p.join()

if __name__ == '__main__':
    run_crawl()
    #crawl_by_page(1, 10)
