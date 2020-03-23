#!/usr/bin/env python3
# -*- coding:utf8 -*-
import re
import csv
import os
import time
from datetime import datetime
from urllib import parse
from concurrent import futures
from pyquery import PyQuery as pq
import requests


localstor='output/D-Link/ftp.dlink.ca/'
executor=None


def download(model, rev, fw_ver, fw_url, rel_date):
    from urllib import request
    from web_utils import getFileSha1, getFileMd5
    try:
        fname = os.path.basename(parse.urlsplit(fw_url).path)

        def epilog():
            sha1 = getFileSha1(localstor+fname)
            md5 = getFileMd5(localstor+fname)
            with open('ca_dlink_filelist.csv', 'a') as fout:
                cw = csv.writer(fout)
                cw.writerow([model,rev,fw_ver, fw_url, rel_date,fsize, sha1, md5])
            return
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

            if not os.path.exists(os.path.dirname(localstor)):
                print("The path dosen't exist, creating one")
                try:
                    os.makedirs(os.path.dirname(localstor))
                except OSError as exc: # Guard against race condition
                    if exc.errno != errno.EEXIST:
                        raise

            with open(localstor+fname, 'wb') as fout:
                fout.write(cont)
            print('finished download :', fw_url)
        epilog()
        return
    except Exception as ex:
        print(ex)


def extract_date(txt):
    for pat in ['%m/%d/%y', '%Y/%m/%d']:
        try:
            return datetime.strptime(txt, pat)
        except ValueError:
            continue
    return None


def extract_fw_ver(txt):
    m = re.search(r'\((.+)\)', txt, re.I)
    if m:
        m2 = re.search(r'[0-9a-z\.]+', m.group(1), re.I)
        return m2.group(0)
    else:
        return None


def crawl_prod(prod_url, model):
    d = pq(url=prod_url)
    revs = [(_.attrib['value'], _.text_content().strip()) for _ in d('select#ddlHardWare option')]
    revs = [(int(revid),revname) for revid,revname in revs if revid]

    for revid,revname in revs:
        epoch = int(time.time()*1000)
        ajax_url='http://support.dlink.ca/ajax/ajax.ashx?'\
            'd=%(epoch)d&action=productfile&lang=en-US&ver=%(revid)d&ac_id=1'\
            %locals()
        ponse = requests.get(url=ajax_url, headers={'Referer':prod_url})
        for it in ponse.json()['item']:
            for fil in it['file']:
                if 'firmware' in fil['name'].lower():
                    fw_ver = extract_fw_ver(fil['name'])
                    date = extract_date(fil['date'])
                    print('%s %s %s %s %s'%(model, revname, fw_ver, fil['url'], date))
                    global executor
                    executor.submit(download, revname, model, fw_ver, fil['url'], date)


def main():
    with open('ca_dlink_filelist.csv', 'w') as fout:
        cw = csv.writer(fout)
        cw.writerow(['model', 'rev', 'fw_ver', 'fw_url', 'date', 'fsize', 'sha1', 'md5'])
    global executor
    executor = futures.ThreadPoolExecutor()

    d = pq(url='http://support.dlink.ca/AllPro.aspx?type=all')
    # all 442 models
    models = [_.text_content().strip() for _ in d('tr > td:nth-child(1) > .aRedirect')]

    for model in models:
        prod_url = 'http://support.dlink.ca/ProductInfo.aspx?m=%s'%parse.quote(model)
        crawl_prod(prod_url, model)
    print('wait for Executor shutdown')
    executor.shutdown(True)


if __name__=='__main__':
    main()
