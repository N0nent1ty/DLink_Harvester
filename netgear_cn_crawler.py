#!/usr/bin/env python3  # noqa
# -*- coding: utf8 -*-
import os
import csv
import re
import traceback
from urllib.parse import urljoin
from urllib.parse import urlsplit
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dateutil.parser import parse as parse_date
import requests
from lxml import html
from form_submit import form_submit
from web_utils import getFileSha1, getFileMd5

visited = {}
executor = None
dlDir = './output/Netgear/support.netgear.cn/'


def main():
    global executor
    try:
        session = requests.Session()
        executor = ThreadPoolExecutor()
        os.makedirs(dlDir, exist_ok=True)
        url = 'http://support.netgear.cn/'
        with open('netgear_cn_filelist.csv', 'w') as fout:
            cw = csv.writer(fout)
            cw.writerow(['model', 'fver', 'fname', 'furl', 'fdate', 'fsize', 'sha1', 'md5'])
        resp = session.get(url=url)
        root = html.fromstring(resp.text)
        startProd = 1
        prods = root.xpath(".//select[@name='select']/option")
        for iProd, prod in enumerate(prods[startProd:], startProd):
            prodText = prod.xpath("./text()")[0].strip()
            prodUrl = prod.xpath("./@value")[0].strip()
            walkProd(session, urljoin(resp.url, prodUrl))
    except BaseException as ex:
        traceback.print_exc()
    finally:
        executor.shutdown(True)


def walkProd(session, url):
    resp = session.get(url)
    root = html.fromstring(resp.text)
    more = root.xpath(".//div[@class='blue']//a")[0]
    walkFiles(session, urljoin(resp.url, more.attrib['href']))


def walkFiles(session, url):
    resp = session.get(url)
    root = html.fromstring(resp.text)
    fwfiles = root.xpath(".//*[@class='linkblue']//a")
    for ifile, fwfile in enumerate(fwfiles):
        fname = fwfile.text_content()
        furl = urljoin(resp.url, fwfile.attrib['href'])
        model = root.xpath(".//*[@class='sizelefttitle']/text()")[0]
        if furl in visited:
            continue
        else:
            visited[furl] = (model,fname,furl)
        download_file(model, fname, furl)


def download_file(model, fdesc, furl):  # noqa
    try:
        with closing(requests.get(url=furl, timeout=10, stream=True)) as resp:
            if 'Content-Length' in resp.headers:
                fsize = int(resp.headers['Content-Length'])
            else:
                fsize = None
            if not fsize:
                print('Unknown size resp.url=%s, headers=%s' %
                      (resp.url, resp.headers) )
                with open('netgear_cn_filelist.csv', 'a') as fout:
                    cw = csv.writer(fout)
                    cw.writerow([model, "", "", furl, None, fsize, "unknown", "unknown"])
                return
            if 'Last-Modified' in resp.headers:
                fdate = resp.headers['Last-Modified']
                fdate = parse_date(fdate)
            else:
                fdate = None
            try:
                fver = re.search(r'\d+(\.\d+)+', fdesc).group(0)
            except AttributeError:
                fver = ''
            needDownload, fname = determine_filename(resp)
            if not needDownload:
                print('Already downloaded: ', fname)
            else:
                print('Start downloading (%d bytes): %s' % (fsize, furl))
                with open(dlDir+fname, 'wb') as fout:
                    fout.write(b'place_holder0')
                with open(dlDir+fname+'.downloading', 'wb') as fout:
                    fout.write(b' '*fsize)
                    # for chunk in resp.iter_content(chunk_size=8192):
                    #    if chunk:  # filter out keep-alive new chunks
                    #        fout.write(chunk)
                try:
                    os.replace(dlDir+fname+'.downloading', dlDir+fname)
                except BaseException as ex:
                    print(ex)
                    print('"%s" not found' % (dlDir+fname+'.downloading'))
                print('Finished downloading: %s' % furl)
            sha1 = getFileSha1(dlDir+fname)
            md5 = getFileMd5(dlDir+fname)
            if fsize and os.path.getsize(dlDir+fname) != fsize:
                print('Content-Length(%s) different to real fsize %s' % (fsize, os.path.getsize(dlDir+fname)))
            fsize = os.path.getsize(dlDir+fname)
            with open('netgear_cn_filelist.csv', 'a') as fout:
                cw = csv.writer(fout)
                cw.writerow([model, fver, fname, furl, fdate, fsize, sha1, md5])
    except requests.exceptions.ConnectionError:
        print('ConnectionError: %s' % furl)
    except BaseException as ex:
        traceback.print_exc()
        import pdb
        pdb.set_trace()


def determine_filename(resp) -> (bool, str):
    try:
        if 'Content-Length' in resp.headers:
            fsize = int(resp.headers['Content-Length'])
        else:
            fsize = None
        if 'Content-Disposition' in resp.headers:
            fname = resp.headers['Content-Disposition']
            fname = fname.split(';')[-1].split('=')[-1].strip(' \t"\'')
        fname = os.path.basename(urlsplit(resp.url).path)
        if not fname:
            import hashlib
            fname = hashlib.md5(resp.url.encode()).hexdigest()
            print('Generate fname "%s" from resp.url="%s"' % (fname, resp.url))
        while True:
            if os.path.isfile(dlDir + fname) and \
                    fsize == os.path.getsize(dlDir + fname):
                return False, fname
            else:
                return True, fname
            ftitle, fext = os.path.splitext(fname)
            m = re.search(r'(.+)_(\d+)', ftitle)
            if m:
                ftitle = '%s_%s' % (m.group(1), int(m.group(2))+1)
                fname = ftitle + fext
            else:
                fname = ftitle + '_1' + fext
    except BaseException as ex:
        traceback.print_exc()


if __name__ == '__main__':
    main()

