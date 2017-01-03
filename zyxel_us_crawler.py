#!/usr/bin/env python3  # noqa
# -*- coding: utf8 -*-
import os
import csv
import re
import sys
import traceback
from urllib.parse import urljoin
from urllib.parse import urlsplit
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dateutil.parser import parse as parse_date
from datetime import datetime
import requests
import ftputil
from lxml import html
from form_submit import form_submit
from web_utils import getFileSha1, getFileMd5


visited = {}
executor = None
dlDir = './output/Zyxel/www.zyxel.com/'


def main():
    global executor
    try:
        session = requests.Session()
        executor = ThreadPoolExecutor(1)
        os.makedirs(dlDir, exist_ok=True)
        url = 'http://www.zyxel.com/us/en/support/download_landing.shtml'
        with open('zyxel_us_linksys.csv', 'w') as fout:
            cw = csv.writer(fout)
            cw.writerow(['model', 'fver', 'fname', 'furl', 'fdate', 'fsize', 'sha1', 'md5'])
        resp = session.get(url=url)
        root = html.fromstring(resp.text)
        models = get_all_models(root)

        for modelName in sorted(models.keys()):
            kbid = models[modelName]
            resp2 = session.get(url='http://www.zyxel.com/us/en/support/DownloadLandingSR.shtml',
                                params=dict(c="us", l="en", kbid=kbid, md=modelName))
            walkFiles(modelName, session, resp2)
    except BaseException as ex:
        traceback.print_exc()
    finally:
        print('Wait for exeuctor shuddown')
        executor.shutdown(True)


def walkFiles(model, session, resp): #noqa
    root = html.fromstring(resp.text)
    for row in root.cssselect('tbody tr'):
        for td in row.cssselect('td'):
            tdclass = td.attrib['class'].split()[0]
            if tdclass == 'typeTd':
                firmware = (td.text_content().strip() == 'Firmware')
            if 'firmware' not in locals() or not firmware:
                continue
            if tdclass == 'versionTd':
                fver = td.text_content().strip()
            elif tdclass == 'noteTd':
                try:
                    anc = td.cssselect('.linkedItem.v1 a')[0]
                    md5 = anc.attrib['data-md5']
                    sha1 = anc.attrib['data-sha1']
                except (IndexError, KeyError):
                    pass
            elif tdclass == 'dateTd':
                fdate = td.text_content().strip()
                fdate = re.search(r'\d+-\d+-\d+', fdate).group(0)
                fdate = datetime.strptime(fdate, "%m-%d-%Y")
            elif tdclass == 'downloadTd':
                furl = td.cssselect('a')[0].attrib.get('data-filelink', '')
                global visited, executor
                if furl not in visited:
                    if 'sha1' not in locals().keys():
                        sha1, md5 = None, None
                    visited[furl] = (model, fver, sha1, md5, fdate)
                    executor.submit(download_file, model, fver, sha1, md5, fdate, furl)


def download_file(model, fver, sha1, md5, fdate, furl):
    try:
        host = ftputil.FTPHost(urlsplit(furl).hostname, "anonymous",
                               "guest@guest.com")
        if not fdate:
            fdate = host.path.getmtime(urlsplit(furl).path)
        fsize = host.path.getsize(urlsplit(furl).path)
        needDownload, fname = determine_filename(host, furl)
        if needDownload:
            fsize = host.path.getsize(urlsplit(furl).path)
            print("Start download %s -> %s %d bytes" % (furl, fname, fsize))
            # host.download(urlsplit(furl).path, dlDir + fname)
            with open(dlDir+fname, 'wb') as fout:
                fout.write(b' '*fsize)
            print("Finished download %s -> %s %d bytes" % (furl, fname, fsize))
        md5 = getFileMd5(dlDir+fname)
        sha1 = getFileSha1(dlDir+fname)
        fsize = os.path.getsize(dlDir+fname)
        with open('zyxel_us_linksys.csv', 'a') as fout:
            cw = csv.writer(fout)
            cw.writerow([model, fver, fname, furl, fdate, fsize, sha1, md5])
    except BaseException as ex:
        traceback.print_exc()
    finally:
        host.close()


def get_all_models(root):
    from lxml import etree
    script = etree.tostring(root.xpath(".//*[@id='searchDropUlWrap']")[0]).decode()
    terms = re.findall('"(.+?)"', script)
    models = {}
    for i in range(6, sys.maxsize, 4):
        try:
            modelName = terms[i]
            kbid = terms[i+3]
            assert modelName not in models.keys()
            models[modelName] = kbid
        except IndexError:
            break
    return models


def determine_filename(host, furl) -> (bool, str):
    try:
        fsize = host.path.getsize(urlsplit(furl).path)
        fname = os.path.basename(urlsplit(furl).path)
        while True:
            if not os.path.exists(dlDir+fname):
                return True, fname  # needDownload=True
            elif os.path.getsize(dlDir + fname) == fsize:
                # same name same size
                return False, fname  # needDownload=False
            # same name different size, change name by appending "_1"
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

