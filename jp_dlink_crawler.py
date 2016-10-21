#!/usr/bin/env python3
# coding: utf-8
import csv
import re
import os
from datetime import datetime
from urllib import parse
from concurrent import futures
from pyquery import PyQuery as pq


localstor='output/D-Link/dlink-jp.com/'
executor=None


def download(model, rev, fw_ver, fw_url, rel_date):
    from urllib import request
    from web_utils import getFileSha1, getFileMd5
    try:
        fname = os.path.basename(parse.urlsplit(fw_url).path)

        def epilog():
            sha1 = getFileSha1(localstor+fname)
            md5 = getFileMd5(localstor+fname)
            with open('jp_dlink_filelist.csv', 'a') as fout:
                cw = csv.writer(fout)
                cw.writerow([model,rev, fw_ver, fw_url, rel_date, fsize, sha1, md5])

        with request.urlopen(fw_url, timeout=60) as fin:
            fsize = fin.headers['Content-Length']
            if os.path.exists(localstor+fname) and \
                    os.path.isfile(localstor+fname) and \
                    os.path.getsize(localstor+fname)==fsize:
                print('%(fname)s already exists'%locals())
                epilog()
                return
            print('start download :', fw_url)
            cont = fin.read()
            with open(localstor+fname, 'wb') as fout:
                fout.write(cont)
            print('finished download :', fw_url)
        epilog()
        return
    except Exception as ex:
        print(ex)


def parse_prod(page_url):
    d = pq(url=page_url)
    model = d('.entry-title>strong')[0].text_content()
    items = d('h4,h5,li')
    for index, item in enumerate(items):
        if 'id' in item.attrib and item.attrib['id']=='product_firmware':
            for li in items[index+1:]:
                if li.tag=='h4':
                    break
                txt = li.text_content().strip()
                if txt.startswith('バージョン'):
                    fw_ver = re.search(r'R\d+[\.a-z0-9]+', txt, re.I).group(0)
                if li.cssselect('div.name strong') and \
                        li.cssselect('div.name strong')[0].text_content().startswith('ファームウェア'):
                    fw_url = li.cssselect('a')[0].attrib['href']
                    rel_date = li.cssselect('div.date')[0].text_content().strip()
                    rel_date = rel_date.replace('//', '/')
                    try:
                        rel_date = re.search('\d+/\d+/\d+', rel_date).group(0)
                        rel_date = datetime.strptime(rel_date, "%Y/%m/%d")
                    except (AttributeError,ValueError):
                        rel_date=None

                    print('%s %s %s'%(model, fw_ver, rel_date))
                    global executor
                    executor.submit(download, model, None, fw_ver, fw_url, rel_date)


def crawl_serie(serie_url):
    d=pq(url=serie_url)
    prods = d('.productList td h3 a')
    for prod in prods:
        model = prod.text_content().strip()
        print('model="%(model)s"'%locals())
        parse_prod(prod.attrib['href'])


root_url="https://www.dlink-jp.com/"


def crawl_cat(caturl):
    d=pq(url=caturl)
    series = d('dd>ul.clearfix>li>a')
    for serie in series:
        path = serie.attrib['href']
        print("serie=%(path)s"%locals())
        serie_url = parse.urljoin(root_url,path)
        crawl_serie(serie_url)


def main():
    with open('jp_dlink_filelist.csv', 'w') as fout:
        cw = csv.writer(fout)
        cw.writerow(['model', 'rev', 'fw_ver', 'fw_url', 'rel_date', 'fsize', 'sha1', 'md5'])
    global executor
    executor = futures.ThreadPoolExecutor()
    os.makedirs(localstor, exist_ok=True)

    d=pq(url=root_url)
    cats = d("#gnav_01 .child p>a")
    for cat in cats:
        path = cat.attrib['href']
        print("cat=%(path)s"%locals())
        caturl = parse.urljoin(root_url,path)
        crawl_cat(caturl)

    d=pq(url="http://www.dlink-jp.com/pog")
    prods = d(".pog_eos a")
    for prod in prods:
        model=prod.text_content().strip()
        print('model="%(model)s"'%locals())
        parse_prod(prod.attrib['href'])

    d=pq(url="http://dlink-jp.com/eos/")
    prods = d(".pog_eos a")
    for prod in prods:
        model=prod.text_content().strip()
        print('model="%(model)s"'%locals())
        parse_prod(prod.attrib['href'])
    print('wait for Executor shutdown')
    executor.shutdown(True)


if __name__=='__main__':
    main()
