#!/usr/bin/env python3  # noqa
# -*- coding: utf8 -*-
import os
import csv
import re
import sys
import traceback
from urllib.parse import urljoin, urlsplit
from concurrent.futures import ThreadPoolExecutor
from dateutil.parser import parse as parse_date
from datetime import datetime
from contextlib import closing
import requests
import ftputil
from lxml import html
from web_utils import getFileSha1, getFileMd5
from pyquery import PyQuery as pq
import html2text
import pdb


visited = {}
executor = None
dlDir = 'output/IpTime/iptime.co.kr/'
driver = None


def download_file(model, fname, furl, fver): #noqa
    from web_utils import getFileSha1, getFileMd5
    from contextlib import closing
    try:
        with closing(requests.get(url=furl, timeout=30, stream=True)) as resp:
            if not resp:
                print("resp.staus_code= ", resp.status_code)
                return
            if 'Content-Length' in resp.headers:
                fsize = int(resp.headers['Content-Length'])
            else:
                fsize = None
            if 'Last-Modified' in resp.headers:
                fdate = resp.headers['Last-Modified']
                fdate = parse_date(fdate)
            else:
                fdate=None
            alreadyDownloaded = False
            if os.path.exists(dlDir+fname) and os.path.getsize(dlDir+fname) == fsize:
                alreadyDownloaded = True
            elif os.path.exists(dlDir+fname) and os.path.getsize(dlDir+fname) != fsize:
                # rename until not os.path.exist(fname)
                while os.path.exists(dlDir+fname):
                    ftitle, fext = os.path.splitext(fname)
                    m = re.search('(.+)_(\d+)', ftitle)
                    if m:
                        ftitle = m.group(1) + '_' + str(int(m.group(2))+1)
                        fname = ftitle+fext
                    else:
                        fname = ftitle+"_1" + fext

            if not alreadyDownloaded:
                print('Start downloading %s -> "%s" %s bytes' % (furl, fname, fsize))
                with open(dlDir+fname, 'wb') as fout:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:  # filter out keep-alive new chunks
                            fout.write(chunk)
                print('Finished downloading %s -> "%s" %s bytes' % (furl, fname, fsize))
            else:
                print('Already downloaded %s' % furl)
            md5 = getFileMd5(dlDir+fname)
            sha1 = getFileSha1(dlDir+fname)
            fsize = os.path.getsize(dlDir+fname)
            with open('iptime_kr_filelist.csv', 'a') as fout:
                cw = csv.writer(fout)
                cw.writerow([model, fver, fname, furl, fdate, fsize, sha1, md5])
    except TimeoutError as ex:
        print('TomeoutError ex=%s, furl=%s' % (ex, furl))
    except BaseException as ex:
        print('ex=%s, furl=%s' % (ex, furl))
        traceback.print_exc()


def walkPageItem(sess, url, pagetitle):
    try:
        resp = sess.get(url=url)
        root = html.fromstring(resp.text)
        try:
            anc = root.xpath(".//span/../../a")[0]
        except IndexError:
            try:
                ancs = root.xpath(".//a")
                anc = next(_ for _ in ancs if '다운로드' in _.text_content())
            except StopIteration:
                print("No download(다운로드) in url= ", url)
                return
        href = anc.attrib.get("href", "")
        href = urljoin(url, href)
        ftitle = root.xpath(".//b")[0].text_content()
        # print('Download "%s", ftitle="%s", ptitle="%s" ' % (href, ftitle, pagetitle))
        model = ftitle.split(" 펌웨어")[0]
        try:
            fver = re.search(r"\d+(\.\d+)+\s*(\(\d+-\d+-\d+\))?", ftitle).group(0)
        except AttributeError:
            if "버전" in ftitle:
                fver = ftitle.split("버전")[-1].strip()
            elif "Ver" in ftitle:
                fver = ftitle.split("Ver")[-1].strip().strip(".")
            else:
                fver = ""
        print('Download fver="%s", model="%s" ' % (fver, model))
        fname = os.path.basename(urlsplit(href).path)
        executor.submit(download_file, model, fname, href, fver)
    except BaseException as ex:
        traceback.print_exc()
        pdb.set_trace()


def walkListItems(sess, url):
    try:
        global visited

        def replacewhite(text):
            return re.sub(r'(\ |\r|\n|\t)+', ' ', text)
        resp = sess.get(url=url)
        root = html.fromstring(resp.text)
        tds = root.xpath(".//*[@class='kboard-list']//tr/td[2]")
        for td in tds:
            href = td.xpath(".//a")[0].attrib['href']
            href = urljoin(url, href)
            href = re.sub(r'pageid=\d+', '', href)
            if href in visited:
                continue
            text = re.sub(r'(\ |\r|\n|\t)+', ' ', td.text_content())
            if '펌웨어' not in text:
                continue
            print(text)
            visited[href] = (text)
            walkPageItem(sess, href, text)
    except BaseException as ex:
        traceback.print_exc()
        print(ex)


def walkNextPages(sess, url="https://iptime.com/iptime/?page_id=126&dffid=1&dfsid=11"):
    try:
        from os.path import basename

        def get_pageid(url):
            from urllib.parse import parse_qsl, urlsplit
            qs = dict(parse_qsl(urlsplit(url).query))
            return int(qs.get("pageid", "1"))
        while True:
            pageid = get_pageid(url)
            print("pageid=%d" % pageid)
            walkListItems(sess, url)

            root = html.fromstring(sess.get(url=url).text)
            arrows = [basename(_) for _ in root.xpath(".//ul[@class='pages']//img/@src")]
            if 'next_1.gif' not in arrows:
                break
            nexturl = next(_ for _ in root.xpath(".//ul[@class='pages']//img") if
                           basename(_.attrib['src']) == 'next_1.gif')
            url = urljoin(url, nexturl.xpath("../../a/@href")[0])
            nextpageid = get_pageid(url)
            assert nextpageid == pageid+1
    except BaseException as ex:
        traceback.print_exc()
        print(ex)


def walkSelects():
    from selenium import webdriver
    from selenium.webdriver.support.ui import Select
    import time
    global driver
    try:
        driver = webdriver.PhantomJS()
        driver.get('https://iptime.com/iptime/?page_id=126')
        # select Firmware "펌웨어"
        driver.find_elements_by_css_selector("#dffid_1")[0].click()
        sess = requests.Session()

        tds = driver.find_elements_by_xpath(".//tbody[1]/tr[2]/td[4]/div[1]/table[1]//td[@id]")
        print("len(tds)=%d" % (len(tds)))
        for itd in range(len(tds)):
            print("itd=%d" % (itd))
            tds[itd].click()
            td = tds[itd]
            while True:
                time.sleep(1)
                visibility = td.find_elements_by_xpath(".//img")[0].get_attribute("style")
                visibility = visibility.split(":")[-1].strip().strip(";")
                if visibility != 'hidden':
                    break
            old_url = driver.current_url
            driver.find_elements_by_xpath(".//tbody[1]/tr[3]/td[2]")[0].click()
            while True:
                time.sleep(1)
                if driver.current_url != old_url:
                    break
            print("url=", driver.current_url)
            time.sleep(1)
            walkNextPages(sess, driver.current_url)
            tds = driver.find_elements_by_xpath(".//tbody[1]/tr[2]/td[4]/div[1]/table[1]//td[@id]")
    except BaseException as ex:
        traceback.print_exc()
        pdb.set_trace()
    finally:
        driver.quit()


def main():
    global executor
    try:
        sess = requests.Session()
        executor = ThreadPoolExecutor()
        os.makedirs(dlDir, exist_ok=True)
        with open('iptime_kr_filelist.csv', 'w') as fout:
            cw = csv.writer(fout)
            cw.writerow(['model', 'fver', 'fname', 'furl', 'fdate', 'fsize', 'sha1', 'md5'])
        walkSelects()
    except BaseException as ex:
        traceback.print_exc()
    finally:
        print('Wait for exeuctor shutdown')
        executor.shutdown(True)


if __name__ == '__main__':
    main()
