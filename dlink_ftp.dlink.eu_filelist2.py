# -*- coding: utf8 -*-

import csv
import os
from os import path
from urllib import parse
from web_utils import getFileSha1
from web_utils import getFileMd5
from datetime import datetime
import traceback
import ipdb
import urllib


localstor='output/D-Link/ftp.dlink.eu/'


def download_file(ftp_url):
    fname = ftp_url.split('/')[-1]
    if os.path.exists(localstor+fname):
        print('aloready downloaded ',fname)
        if os.path.getsize(localstor+fname)>0:
            return localstor+fname
        ftitle,fext = path.splitext(fname)
        fname = ftitle+'_001'+fext
        print('prevent overwrite, use "%s"'%(localstor+fname))
    from urllib import request
    with request.urlopen(ftp_url,timeout=30) as fin:
        with open(localstor+fname, 'wb') as fout:
            data = fin.read()
            fout.write(data)
            return localstor+fname


def get_ftp_date(url):
    import ftputil
    pr = parse.urlsplit(url)
    with ftputil.FTPHost(pr.netloc, 'anonymous', '') as host:
        return host.path.getmtime(pr.path)


def make_abs_url(url):
    pr = parse.urlsplit(url)
    return parse.urlunsplit(parse.SplitResult(pr.scheme, pr.netloc, path.abspath(pr.path), '',''))


def parse_date(txt):
    if not txt:
        return None
    try:
        return datetime.strptime(txt, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        ipdb.set_trace()


def guess_date(ftp_url):
    import re
    m = re.search(r'_\d{6,8}', ftp_url.split('/')[-1])
    if not m:
        return None
    m = m.group(0).strip('_')
    if len(m)==6:
        return datetime.strptime(m,'%y%m%d')
    elif len(m)==8:
        return datetime.strptime(m,'%Y%m%d')
    else:
        ipdb.set_trace()


try:
    with open('dlink_ftp.dlink.eu_filelist2.csv', 'r') as fin:
        cr = csv.reader(fin)
        next(cr)
        rows = [[model,fw_ver, url,int(size), parse_date(date), sha1,md5] for model,fw_ver,url,size,date,sha1,md5 in cr]
    rows = [_ for _ in rows if _[0]]  # filter out empty model name
    for i,row in enumerate(rows):
        if not row[4]:
            rows[i][4] = guess_date(row[2])

    nullshas = [i for i,_ in enumerate(rows) if not _[5]]
    nullshas.sort(reverse=True)
    for index in nullshas:
        index
        model, fw_ver, ftpurl, file_size, file_date, _,_ = rows[index]
        if '../' in ftpurl:
            ftpurl = make_abs_url(ftpurl)
        try:
            solid_index = next(i for i,_ in enumerate(rows) if _[2]==ftpurl and _[5] and i!=index)
            print('Merge "%s" "%s"'%(model, fw_ver))
            solid_file_size, solid_date,file_sha1, file_md5 = rows[solid_index][3:7]
            assert file_sha1
            if file_date is None:
                file_date = solid_date
            rows[solid_index] = model, fw_ver, ftpurl, solid_file_size, file_date, file_sha1, file_md5
            del rows[index]
        except StopIteration:
            print('Download %s'%ftpurl)
            try:
                fname = download_file(ftpurl)
            except urllib.error.URLError:
                print('Failed to download ', ftpurl)
                continue
            file_sha1 = getFileSha1(fname)
            file_md5 = getFileMd5(fname)
            file_size = os.path.getsize(fname)
            rows[index][3]=file_size
            if rows[index][4] is None:
                get_ftp_date(ftpurl)
            rows[index][5]=file_sha1
            rows[index][6]=file_md5

    rows.sort(key=lambda r:(r[0].lower(),r[1].lower(),r[2].lower()))
    with open('dlink_ftp.dlink.eu_filelist3.csv', 'w') as fout:
        cw = csv.writer(fout)
        cw.writerow(['model','fw_ver','fw_url','size','date','sha1','md5'])
        cw.writerows(rows)

except Exception as ex:
    traceback.print_exc()
    ipdb.set_trace()


