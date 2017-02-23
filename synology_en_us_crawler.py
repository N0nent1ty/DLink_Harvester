#!/usr/bin/env python3 #noqa
import re
import os
import requests
from contextlib import closing
from urllib.parse import urljoin, urlsplit
from concurrent.futures import ThreadPoolExecutor
import json
import csv
from lxml import html
from datetime import datetime
from dateutil.parser import parse as parse_date
from web_utils import getFileSha1, getFileMd5
import traceback


visited = {}
executor = None
dlDir = 'output/Synology/www.synology.com/'


def main():
    global executor
    try:
        sess = requests.Session()
        executor = ThreadPoolExecutor()
        os.makedirs(dlDir, exist_ok=True)
        url = "https://www.synology.com/en-us/support/download"
        with open('Synology_en_us.csv', 'w') as fout:
            cw = csv.writer(fout)
            cw.writerow(['model', 'fver', 'furl', 'fname', 'fdate', 'fsize', 'sha1', 'md5'])
        resp = sess.get(url=url)
        texts = resp.text.splitlines()
        i = next(i for i,_ in enumerate(texts) if _.strip().startswith("var list ="))
        j = next(j for j,_ in enumerate(texts[i+1:], i+1) if _.strip().startswith("var oemList ="))
        text = ''.join(_.strip() for _ in texts[i:j])
        # typemodels = re.findall('"(\w+)":\["([\w\+\-]+)"', text)
        models = re.findall('"([\w\+\-\ ]+)"', text)
        for model in models:
            print('model=("%s")' % (model))
            resp = sess.get(url="https://www.synology.com/cgi/support",
                            params=dict(action="findDownloadInfo",
                                        product=model, lang="en-us"))
            try:
                dsm = resp.json()['info']['dsm']
            except KeyError:
                print('model="%s" not found' % model)
                continue
            if dsm is None:
                print('model="%s" not found' % model)
                continue
            fdate = dsm['publish_date']
            fdate = datetime.strptime(fdate, "%Y-%m-%d")
            fver = dsm['version']
            fver = re.search(r'\d+(\.\d+)*(-\d+)?', fver).group(0)
            furl = dsm['download']
            print('submit %s %s' % (model, furl))
            executor.submit(download_file,model, fver, fdate, furl)
    except BaseException as ex:
        traceback.print_exc()
    finally:
        print('Wait for exeuctor shuddown')
        executor.shutdown(True)



def download_file(model, fver, fdate, furl): # noqa
    try:
        with closing(requests.get(url=furl, timeout=30, stream=True)) as resp:
            if 'Content-Length' in resp.headers:
                fsize = int(resp.headers['Content-Length'])
            else:
                fsize = None
            if not fdate:
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
            with open('Synology_en_us.csv', 'a') as fout:
                cw = csv.writer(fout)
                cw.writerow([model, fver, furl, fname, fdate, fsize, sha1, md5])
    except TimeoutError as ex:
        print('TomeoutError ex=%s, furl=%s' % (ex, furl))
    except BaseException as ex:
        print('ex=%s, furl=%s' % (ex, furl))
        traceback.print_exc()


if __name__ == '__main__':
    main()
