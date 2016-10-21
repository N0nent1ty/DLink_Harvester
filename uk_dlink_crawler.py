#!/usr/bin/env python3
# coding: utf-8
import re
import os
import csv
import urllib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from pyquery import PyQuery as pq


executor=None
localstor='output/D-Link/ftp.dlink.eu/'


def download(model, rev, fw_ver, fw_url, fdate):
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
            with open('uk_dlink_filelist.csv', 'a') as fout:
                cw = csv.writer(fout)
                cw.writerow([model, rev, fw_ver, fw_url, fsize, fdate, sha1, md5])
            return
        from urllib import parse
        fw_path = parse.urlsplit(fw_url).path
        netloc = parse.urlsplit(fw_url).netloc
        with ftputil.FTPHost(netloc, 'anonymous', '') as host:
            if not host.path.isfile(fw_path):
                print('"ftp://%s/%s" does not exist.'%(netloc,fw_path))
                epilog(-1, None)
                return
            fsize = host.path.getsize(fw_path)
            if fdate is None:
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


def extract_fw_ver(txt):
    m = re.search(r'\d+\.\d+[a-z]*\d*', txt, re.I)
    return m.group(0) if m else None


def parse_page(page_url, model):
    try:
        d = pq(url=page_url)
        options = d('select.download-select > option')
        for o in options:
            if 'Firmware' in o.attrib['data-tracking']:
                fw_ver = extract_fw_ver(o.text_content())
                if fw_ver is None:
                    # divs = [_.text_content().splitlines()[1].strip() for _ in d('div.dataTable')]
                    # print('%s'%divs)
                    continue
                fw_url = o.attrib['data-url']
                fdate = o.attrib['data-date']
                if fdate!='-':
                    for pat in ['%d/%m/%Y', '%d/%m/%y']:
                        try:
                            fdate = datetime.strptime(fdate, pat)
                            break
                        except ValueError:
                            continue
                    assert type(fdate) is datetime
                else:
                    fdate=None
                print('%s %s %s %s'%(model,fw_ver,fw_url,fdate))
                global executor
                executor.submit(download, model, None, fw_ver,fw_url,fdate)
    except urllib.error.HTTPError as ex:
        print(ex, ' url=', page_url)
    except Exception as ex:
        print(ex)
        import pdb
        pdb.set_trace()
        import traceback
        traceback.print_exc()


def main():
    global executor
    executor = ThreadPoolExecutor()
    os.makedirs(localstor, exist_ok=True)

    with open('uk_dlink_filelist.csv', 'w') as fout:
        cw = csv.writer(fout)
        cw.writerow(['model', 'rev', 'fw_ver', 'fw_url', 'fsize', 'fdate', 'sha1', 'md5'])
    
    d = pq(url='http://www.dlink.com/uk/en/support/all-products?tab=all&po=true')
    for item in d('.support_popular_products > ul > li > a'):
        model = item.text_content().strip()
        parse_page(item.attrib['href'], model)
    print('wait for Executor shutdown')
    executor.shutdown(True)


if __name__=='__main__':
    main()
