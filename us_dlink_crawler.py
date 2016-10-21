#!/usr/bin/env python3
# -*- coding:utf8 -*-
import re
import os
import csv
import time
from datetime import datetime
from urllib import parse
from concurrent.futures import ThreadPoolExecutor
from pyquery import PyQuery as pq
import requests


executor=None
localstor='output/D-Link/ftp2.dlink.com/'


def download(model, rev, fw_ver, fw_url):
    from web_utils import getFileSha1, getFileMd5
    import ftputil
    try:
        fname = fw_url.split('/')[-1]

        def epilog(fsize, fdate):
            if not os.path.isfile(localstor+fname):
                sha1=None
                md5=None
            else:
                sha1 = getFileSha1(localstor+fname)
                md5 = getFileMd5(localstor+fname)
            with open('us_dlink_filelist.csv', 'a') as fout:
                cw = csv.writer(fout)
                cw.writerow([model, rev, fw_ver, fw_url, fsize, fdate, sha1, md5])
            return
        from urllib import parse
        fw_path = parse.urlsplit(fw_url).path
        netloc = parse.urlsplit(fw_url).netloc
        with ftputil.FTPHost(netloc, 'anonymous', '') as host:
            if not host.path.isfile(fw_path):
                print('"%s" does not exist.'%fw_path)
                epilog(-1, None)
                return
            fsize = host.path.getsize(fw_path)
            fdate = host.path.getmtime(fw_path)
            if os.path.isfile(localstor+fname) and os.path.getsize(localstor+fname)==fsize:
                print('%(fname)s already exists'%locals())
                epilog(fsize,fdate)
                return
            print('Start downloading %(fw_url)s'%locals())
            host.download(fw_path, localstor+fname)
            print('Finised downloading %(fw_url)s'%locals())
            epilog(fsize,fdate)
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
        return m.group(1).strip(' \t()')
    else:
        return None


def crawl_prod(prod_url, model):
    d = pq(url=prod_url)
    revs = [(_.attrib['value'], _.text_content().strip()) for _ in d('select#ddlHardWare option')]
    revs = [(int(revid),revname) for revid,revname in revs if revid]

    for revid,revname in revs:
        epoch = int(time.time()*1000)
        ajax_url='http://support.dlink.com/ajax/ajax.ashx?d=%(epoch)d&action=productfile&'\
            'lang=en-US&ver=%(revid)d&ac_id=1'%locals()
        ponse = requests.get(url=ajax_url, headers={'Referer':prod_url})
        for it in ponse.json()['item']:
            for fil in it['file']:
                if 'firmware' in fil['name'].lower():
                    fw_ver = extract_fw_ver(fil['name'])
                    date = extract_date(fil['date'])
                    print('%s %s %s %s %s'%(model, revname, fw_ver, fil['url'], date))
                    try:
                        global executor
                        executor.submit(download, model, revname, fw_ver, fil['url'])
                    except Exception as ex:
                        print(ex)
                        import traceback
                        traceback.print_exc()


def main():
    global executor
    executor=ThreadPoolExecutor()

    os.makedirs(localstor, exist_ok=True)

    with open('us_dlink_filelist.csv', 'w') as fout:
        cw = csv.writer(fout)
        cw.writerow(['model', 'rev', 'fw_ver', 'fw_url', 'fsize', 'fdate', 'sha1', 'md5'])

    start_url="http://support.dlink.com/AllPro.aspx?type=all"
    d = pq(url=start_url)
    # all 442 models
    models = [_.text_content().strip() for _ in d('tr > td:nth-child(1) > .aRedirect')]

    for model in models:
        prod_url = "http://support.dlink.com/ProductInfo.aspx?m=%s"%parse.quote(model)
        crawl_prod(prod_url, model)
    executor.shutdown(True)


if __name__=='__main__':
    main()
