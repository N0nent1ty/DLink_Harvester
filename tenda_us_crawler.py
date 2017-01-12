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
import html2text


visited = {}
executor = None
dlDir = 'output/Tenda/www.tendaus.com/'


def main():
    global executor
    try:
        sess = requests.Session()
        executor = ThreadPoolExecutor()
        os.makedirs(dlDir, exist_ok=True)
        with open('tenda_us_filelist.csv', 'w') as fout:
            cw = csv.writer(fout)
            cw.writerow(['model', 'fver', 'fname', 'furl', 'fdate', 'fsize', 'sha1', 'md5'])
        walkModels(sess, 'http://www.tendaus.com/Default.aspx?Module=WebsiteEN&Action=DownloadCenter')
        walkTables(sess, "http://www.tendaus.com/Default.aspx?Module=WebsiteEN&Action=DownloadCenter&Id=57")
        walkTables(sess, "http://www.tendaus.com/Default.aspx?Module=WebsiteEN&Action=DownloadCenter&Id=59")
        walkTables(sess, "http://www.tendaus.com/Default.aspx?Module=WebsiteEN&Action=DownloadCenter&Id=39")
    except BaseException as ex:
        traceback.print_exc()
    finally:
        print('Wait for exeuctor shutdown')
        executor.shutdown(True)


def walkModels(sess, url):
    resp = sess.get(url=url)
    root = html.fromstring(resp.text)
    models = root.cssselect("#proSearch>li>a")
    for model in models:
        # text = model.text_content()
        # print('model=', text)
        href = model.cssselect('a')[0].attrib['href']
        walkTables(sess, urljoin(url, href))


def walkTables(sess, url):
    resp = sess.get(url=url)
    print('walkTables url=', url)
    root = html.fromstring(resp.text)
    tables = root.xpath(".//table[@bgcolor='#ddd']")
    model = root.cssselect("h1")[0].text_content().strip()
    model = re.sub(r"Download|for","", model, re.I).strip()
    print('model="%s"' % (model))
    for table in tables:
        fver, fdate = None,None
        for td in table.xpath(".//td"):
            if td.xpath('.//@href'):
                fname = td.xpath(".//text()")[0]
                furl = urljoin(url, td.xpath('.//@href')[0])
            for text in [_.strip() for _ in td.xpath('.//text()') if _.strip()]:
                m = re.search(r'\d{4}-\d{2}-\d{2}', text)
                if m:
                    fdate = datetime.strptime(m.group(0), "%Y-%m-%d")
                m = re.search(r"V\d+(\.\d+)*", text)
                if m:
                    fver = m.group(0)
        global executor,visited
        if furl not in visited:
            visited[furl] = (model,fver,fdate,furl)
            executor.submit(download_file,model, fname, furl, fver, fdate)


def download_file(model, fname, furl, fver, fdate): #noqa
    try:
        with closing(requests.get(url=furl, timeout=30, stream=True)) as resp:
            if 'Content-Length' in resp.headers:
                fsize = int(resp.headers['Content-Length'])
            else:
                fsize = None
            if 'Last-Modified' in resp.headers and not fdate:
                fdate = resp.headers['Last-Modified']
                fdate = parse_date(fdate)
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
            with open('tenda_us_filelist.csv', 'a') as fout:
                cw = csv.writer(fout)
                cw.writerow([model, fver, fname, furl, fdate, fsize, sha1, md5])
    except TimeoutError as ex:
        print('TomeoutError ex=%s, furl=%s' % (ex, furl))
    except BaseException as ex:
        print('ex=%s, furl=%s' % (ex, furl))
        traceback.print_exc()


if __name__ == '__main__':
    main()
