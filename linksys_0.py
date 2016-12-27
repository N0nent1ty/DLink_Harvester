#!/usr/bin/env python3  # noqa
# -*- coding: utf8 -*-
import re
import os
import csv
import traceback
from urllib.parse import urljoin
from urllib.parse import urlsplit
from contextlib import closing
from lxml import html
from concurrent.futures import ThreadPoolExecutor
import requests
from dateutil.parser import parse as parse_date
from web_utils import getFileSha1, getFileMd5


executor = None
dlDir = './output/linksys/0/'


def main():
    global executor
    os.makedirs(dlDir)
    executor = ThreadPoolExecutor()
    with open('linksys_filelist.csv', 'w') as fout:
        cw = csv.writer(fout)
        cw.writerow(['model', 'hw_rev', 'fver', 'furl', 'fdate', 'fsize', 'sha1', 'md5'])
    session = requests.Session()
    selectProduct(session, 'http://www.linksys.com/us/support/sitemap/')


def selectProduct(session, mainUrl):
    startProd = 0
    resp = session.get(mainUrl)
    tree = html.fromstring(resp.text)
    for iProd, prod in enumerate(tree.cssselect('.item>ul>li>a')[startProd:], startProd):
        print('%d prod=%s' % (iProd, prod.text_content()))
        prodText = prod.text_content()
        href = prod.attrib['href']
        selectSupport(session, urljoin(resp.url, href))


def selectSupport(session, prodUrl):
    resp = session.get(prodUrl)
    tree = html.fromstring(resp.text)
    for iSupport, support in enumerate(tree.cssselect('.row>p>a')):
        print('support=', support.text_content().strip())
        if 'download' in support.text_content().lower():
            selectFile(session, urljoin(resp.url, support.attrib['href']))


def dom2text(dom, ignore_images=True, ignore_emphasis=True, ignore_tables=True):
    from lxml import etree
    import html2text
    htt = html2text.HTML2Text()
    htt.body_width = 0
    htt.ignore_images = ignore_images
    htt.ignore_emphasis = ignore_emphasis
    htt.ignore_tables = ignore_tables
    return htt.handle(etree.tostring(dom).decode())


def selectFile(session, fileUrl): # noqa
    resp = session.get(fileUrl)
    tree = html.fromstring(resp.text)
    contents = tree.cssselect('.article-accordian-content')
    accordians = tree.cssselect('.article-accordian')
    model = tree.cssselect('.article-header>h1')[0].text_content()
    model = model.replace('Downloads', '').strip()
    for iCont, content in enumerate(contents):
        try:
            hw_rev = accordians[iCont].text_content().strip()
        except IndexError:
            print('len(contents)=%d , but len(accordians)=%d' %
                  (len(contents), len(accordians)))
            break
        try:
            hw_rev = re.search(r'\d+(\.\d+)+', hw_rev).group(0)
        except AttributeError:
            hw_rev = re.sub(r'For| ', '', hw_rev, re.I)
            hw_rev = hw_rev.strip()
        print('hw_rev=', hw_rev)
        text = dom2text(content)
        firmware = False
        for line in text.splitlines():
            if not line.strip():
                continue
            elif line.strip().startswith('#'):
                firmware = 'firmware' in line.lower()
            elif 'Firmware' in line.strip():
                firmware = True
            elif 'Version:' in line:
                fver = line.split(':')[-1].strip()
                try:
                    fver = re.search(r'\d+(\.\d+)+', fver).group(0)
                except AttributeError:
                    pass
            elif line.startswith('Ver'):
                try:
                    fver = re.search(r'\d+(\.\d+)+', line).group(0)
                except AttributeError:
                    pass
            elif re.search(r'\bDate\b', line, re.I):
                try:
                    fdate = line.split(':')[-1].strip()
                    fdate = parse_date(fdate)
                except AttributeError:
                    continue
            elif '[Download]' in line:
                furl = re.search(r'\((.+)\)', line).group(1)
                if firmware:
                    if 'fver' not in locals().keys():
                        fver = '1.0'
                    print('hw_rev, model, fver, fdate, furl ', hw_rev, model, fver, fdate, furl)
                    global executor
                    executor.submit(download_file, hw_rev, model, fver, fdate, furl)


def download_file(hw_rev, model, fver, fdate, furl):  #noqa
    try:
        with closing(requests.get(url=furl, timeout=10, stream=True)) as resp:
            if 'Last-Modified' in resp.headers:
                fdate = resp.headers['Last-Modified']
                fdate = parse_date(fdate)
            if 'Content-Disposition' in resp.headers:
                fname = resp.headers['Content-Disposition']
                fname = fname.split(';')[-1].split('=')[-1].strip()
            if 'Content-Length' in resp.headers:
                fsize = resp.headers['Content-Length']
                fsize = int(fsize)
            fname = os.path.basename(urlsplit(furl).path)
            if os.path.isfile(dlDir + fname) \
                    and fsize == os.path.getsize(dlDir + fname):
                print('already downloaded: ', fname)
            else:
                print('start downloading: ', furl)
                with open(dlDir + fname + '.downloading', 'wb') as fout:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:  # filter out keep-alive new chunks
                            fout.write(chunk)
                try:
                    os.rename(dlDir + fname + '.downloading', dlDir + fname)
                except FileNotFoundError:
                    print('"%s" not found' % (dlDir + fname + '.downloading'))
                print('finished downloading: ', furl)
            sha1 = getFileSha1(dlDir + fname)
            md5 = getFileMd5(dlDir + fname)
            if fsize and os.path.getsize(dlDir + fname) != fsize:
                print('Content-Length(%s) different to real fsize %s' %
                      (fsize, os.path.getsize(dlDir+fname)))
            fsize = os.path.getsize(dlDir + fname)
            with open('linksys_filelist.csv', 'a') as fout:
                cw = csv.writer(fout)
                cw.writerow([model, hw_rev, fver, furl, fdate, fsize, sha1, md5])
    except BaseException as ex:
        traceback.print_exc()
        import pdb
        pdb.set_trace()


if __name__ == '__main__':
    main()

