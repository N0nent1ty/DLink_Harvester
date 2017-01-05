#!/usr/bin/env python3  # noqa
# -*- coding: utf8 -*-
import os, csv, re, sys # noqa
import traceback
import unicodedata
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

visited = {}
executor = None
dlDir = 'output/Tenda/www.tendacn.com'


def main():
    global executor
    try:
        session = requests.Session()
        executor = ThreadPoolExecutor()
        os.makedirs(dlDir, exist_ok=True)
        with open('tenda_filelist.csv', 'w') as fout:
            cw = csv.writer(fout)
            cw.writerow(['model', 'fver', 'fname', 'furl', 'fdate', 'fsize', 'sha1', 'md5'])
        url = 'http://www.tendacn.com/en/service/download-cata-11.html'
        d = pq(url=url)
        anchors = d('.SearchFaqList.clearfix>dd>a')
        for anchor in anchors:
            text = unicodedata.normalize('NFKC', anchor.text_content())
            model = text.split()[0]
            fver = re.search(r'V\d+(\.\d+)+', text, re.I).group(0)
            download_file(model, fver, text, anchor.attrib['href'])
    except BaseException as ex:
        traceback.print_exc()
    finally:
        print('Wait for exeuctor shuddown')
        executor.shutdown(True)


def download_file(model, fver, text, furl): #noqa
    try:
        with closing(requests.get(url=furl, timeout=30, stream=True)) as resp:
            if 'Content-Length' in resp.headers:
                fsize = int(resp.headers['Content-Length'])
            else:
                fsize = None
            if 'Last-Modified' in resp.headers:
                fdate = resp.headers['Last-Modified']
                fdate = parse_date(fdate)
            fname = os.path.basename(urlsplit(furl).path)
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
                print('Start downloading %s -> "%s" %d bytes' % (furl, fname, fsize))
                with open(dlDir+fname, 'wb') as fout:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:  # filter out keep-alive new chunks
                            fout.write(chunk)
                print('Finished downloading %s -> "%s" %d bytes' % (furl, fname, fsize))
            else:
                print('Already downloaded %s' % furl)
            md5 = getFileMd5(dlDir+fname)
            sha1 = getFileSha1(dlDir+fname)
            fsize = os.path.getsize(dlDir+fname)
            with open('tenda_filelist.csv', 'a') as fout:
                cw = csv.writer(fout)
                cw.writerow([model, fver, fname, furl, fdate, fsize, sha1, md5])
    except TimeoutError as ex:
        print('TomeoutError ex=%s, furl=%s' % (ex, furl))
    except BaseException as ex:
        print('ex=%s, furl=%s' % (ex, furl))
        traceback.print_exc()


if __name__ == '__main__':
    main()

