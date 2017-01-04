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


visited = {}
executor = None
dlDir = 'output/Zyxel/www.zyxel.com/'


def main():
    global executor
    try:
        session = requests.Session()
        executor = ThreadPoolExecutor()
        os.makedirs(dlDir, exist_ok=True)
        url = 'http://www.zyxel.com/us/en/support/download_landing.shtml'
        with open('zyxel_us_filelist.csv', 'w') as fout:
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
                if firmware:
                    print('Download "%s" firmware' % model)
            if 'firmware' not in locals() or not firmware:
                continue
            if tdclass == 'versionTd':
                fver = td.text_content().strip()
            elif tdclass == 'dateTd':
                fdate = td.text_content().strip()
                fdate = re.search(r'\d+-\d+-\d+', fdate).group(0)
                fdate = datetime.strptime(fdate, "%m-%d-%Y")
            elif tdclass == 'downloadTd':
                furl = td.cssselect('a')[0].attrib.get('data-filelink', '')
                if furl:
                    print('furl=%s' % furl)
                else:
                    print('furl is empty!!!')
                global visited, executor
                if furl and furl not in visited:
                    visited[furl] = (model, fver, fdate)
                    # executor.submit(download_file, model, fver, fdate, furl)
                    download_file(model, fver, fdate, furl)


def download_file(model, fver, fdate, furl):
    if urlsplit(furl).scheme == 'ftp':
        download_ftp_file(model, fver, fdate, furl)
    elif urlsplit(furl).scheme.startswith('http'):
        download_http_file(model, fver, fdate, furl)


def download_ftp_file(model, fver, fdate, furl):
    try:
        host = ftputil.FTPHost(urlsplit(furl).hostname, "anonymous",
                               "guest@guest.com")
    except ftputil.error.FTPOSError as ex:
        print('ex=%s, furl=%s' % (ex, furl))
        return
    try:
        host.keep_alive()
        if not fdate:
            fdate = host.path.getmtime(urlsplit(furl).path)
        fsize = host.path.getsize(urlsplit(furl).path)
        needDownload, fname = determine_ftp_filename(host, furl)
        if needDownload:
            fsize = host.path.getsize(urlsplit(furl).path)
            print("Start download %s -> \"%s\" %d bytes" % (furl, fname, fsize))
            host.download(urlsplit(furl).path, dlDir + fname)
            print("Finished download \"%s\" -> %s %d bytes" % (furl, fname, fsize))
        else:
            print('Already downloaded %s' % (furl))
        md5 = getFileMd5(dlDir+fname)
        sha1 = getFileSha1(dlDir+fname)
        fsize = os.path.getsize(dlDir+fname)
        with open('zyxel_us_filelist.csv', 'a') as fout:
            cw = csv.writer(fout)
            cw.writerow([model, fver, fname, furl, fdate, fsize, sha1, md5])
    except TimeoutError as ex:
        print('Tomeout Error ex=%s, furl=%s' % (ex, furl))
    except BaseException as ex:
        print('ex=%s, furl=%s' % (ex, furl))
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


def determine_ftp_filename(host, furl) -> (bool, str):
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


def download_http_file(model, fver, fdate, furl): # noqa
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
            with open('zyxel_us_linksys.csv', 'a') as fout:
                cw = csv.writer(fout)
                cw.writerow([model, fver, fname, furl, fdate, fsize, sha1, md5])
    except TimeoutError as ex:
        print('TomeoutError ex=%s, furl=%s' % (ex, furl))
    except BaseException as ex:
        print('ex=%s, furl=%s' % (ex, furl))
        traceback.print_exc()


if __name__ == '__main__':
    main()

