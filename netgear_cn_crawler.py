#!/usr/bin/env python3  # noqa
# -*- coding: utf8 -*-
import os
import csv
import re
import traceback
from urllib.parse import urljoin
from urllib.parse import urlsplit
from concurrent.futures import ThreadPoolExecutor
from dateutil.parser import parse as parse_date
import requests
from lxml import html
from form_submit import form_submit
from web_utils import getFileSha1, getFileMd5
from contextlib import closing

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
        download_file(model, fname, furl)


if __name__ == '__main__':
    main()

