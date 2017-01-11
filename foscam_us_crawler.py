#!/usr/bin/env python3  # noqa
# -*- coding: utf8 -*-
import os, csv, re, sys # noqa
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


visited = {}
executor = None
dlDir = 'output/Foscam/www.foscam.com/'


def get_model(text):
    models = re.split(r' |\ |,|\t|\r|\n', text)
    for model in models:
        m = re.search(r'FI\d+[A-Z]( V\d)?', model)
        if m:
            model = m.group(0)
            return model
    return text


def get_fver(text):
    m = re.search(r'(V-)?\d+(\.[0-9xX]+)*(-\d+)?', text)
    if m:
        fver = m.group(0)
        return fver
    return text


def main():
    global executor
    try:
        sess = requests.Session()
        executor = ThreadPoolExecutor()
        os.makedirs(dlDir, exist_ok=True)
        with open('foscam_filelist.csv', 'w') as fout:
            cw = csv.writer(fout)
            cw.writerow(['model', 'fver', 'fname', 'furl', 'fdate', 'fsize', 'sha1', 'md5'])
        resp1 = sess.get(url='http://www.foscam.com/index.php/home/index/signin.html')
        data = dict(Email='acteam.grid@gmail.com', password='Foscam2017', remember='on')
        resp2 = sess.post(url='http://www.foscam.com/index/login', data=data)
        resp = sess.get(url='http://www.foscam.com/download-center/firmware-downloads.html')
        root = html.fromstring(resp.text)
        spans = [_ for _ in root.cssselect('#main_right>span>p') if _.text_content().strip()]
        from collections import deque
        dq = deque()
        for i, span in enumerate(spans):
            text = span.text_content().strip()
            if text == 'download':
                if len(dq) <= 3:
                    model = spans[i-3].text_content().strip()
                    fver = spans[i-2].text_content().strip()
                    model = get_model(model)
                    fver = get_fver(fver)
                    furl = span.cssselect('a')[0].attrib['href']
                    dq.clear()
                    global visited
                    if furl not in visited:
                        visited[furl] = (model, fver)
                        download_file(model, fver, furl)
                else:
                    model = spans[i-5].text_content().strip()
                    fver = spans[i-4].text_content().strip()
                    model = get_model(model)
                    fver = get_fver(fver)
                    furl = span.cssselect('a')[0].attrib['href']
                    dq.clear()
                    global visited
                    if furl not in visited:
                        visited[furl] = (model, fver)
                        download_file(model, fver, furl)
            else:
                dq.append(span)
    except BaseException as ex:
        traceback.print_exc()
    finally:
        print('Wait for exeuctor shuddown')
        executor.shutdown(True)



def download_file(model, fver, furl): # noqa
    try:
        with closing(requests.get(url=furl, timeout=30, stream=True)) as resp:
            fsize = None
            if 'Content-Length' in resp.headers:
                fsize = int(resp.headers['Content-Length'])
            fdate = None
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
            with open('foscam_filelist.csv', 'a') as fout:
                cw = csv.writer(fout)
                cw.writerow([model, fver, fname, furl, fdate, fsize, sha1, md5])
    except TimeoutError as ex:
        print('TomeoutError ex=%s, furl=%s' % (ex, furl))
    except BaseException as ex:
        print('ex=%s, furl=%s' % (ex, furl))
        traceback.print_exc()


if __name__ == '__main__':
    main()

