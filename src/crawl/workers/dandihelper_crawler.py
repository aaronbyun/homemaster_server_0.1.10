# -*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import requests as req
import multiprocessing as mp
from pymongo import MongoClient
from bs4 import BeautifulSoup


def crawl_by_page(start, end):
    #mongo = MongoClient('59.10.152.219', 27017)
    #db = mongo.worker

    host = 'http://www.dandihelper.com/'

    page_url = host + 'html/s02.html?area1=&area2=&radio_area1=on&shape=&sphere%5B%5D=%B0%A1%BB%E7%B5%B5%BF%EC%B9%CC&sphere%5B%5D=%C3%BB%BC%D2%B5%B5%BF%EC%B9%CC&newname=&career=&nationality=%C7%D1%B1%B9%C0%CE&sex=&x=40&y=11&page={page}'
    session = req.Session()

    params = {'href_self' : 'http://www.dandihelper.com//index.html', 'hrefqry' : '', 'userid' : 'homemaster', 'pwd' : 'homemaster1!', 'x' : 54, 'y' : 17}
    res = session.post('https://www.dandihelper.com/member/login_ok.php', data=params, verify=True, headers = {'Cookie' : 'PHPSESSID=d4563e821a6608b5d9657f57fe177ea0; goods_num=75124%2C76562%2C124099; goods_page=%2Fhtml%2Fs02_v.html%2C%2Fhtml%2Fs02_v.html%2C%2Fhtml%2Fs01_v.html; _gat=1; wcs_bt=s_7673cfbdb71:1453136247; _ga=GA1.2.394758167.1453031162', 'User-Agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36'})

    for i in xrange(end-start+1):
        page_num = start + i

        page_url = page_url.replace('{page}', str(page_num))
        print page_url
        crawl_urls = get_crawl_urls(page_url)

        for url in crawl_urls:
            #res = session.get(host + url, cookies=session.cookies.get_dict())
            print url


def get_crawl_urls(url):
    res = req.get(url)
    res.encoding = 'euc-kr'
    soup = BeautifulSoup(res.text)
    
    crawl_urls = []
    print soup
    assistants = soup.find('div', attrs = {'class' : 'assistant'})

    for line in assistants.find_all('tr'):
        link = line.find('a', attrs = {'title' : '이름 나이/결혼/자녀수'})['href']
        crawl_urls.append(link)
    
    return crawl_urls


def run_crawl():
    num_proc = 10
    page_indexes = [(10*i+1, 10*(i+1)) for i in range(10)]
    procs = [mp.Process(target=crawl_by_page, args=(pi[0], pi[1])) for pi in page_indexes]

    for p in procs:
        p.start()

    for p in procs:
        p.join()

if __name__ == '__main__':
    run_crawl()
