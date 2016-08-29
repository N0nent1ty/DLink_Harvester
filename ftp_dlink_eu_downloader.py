#!/usr/bin/env python3
# -*- coding: utf8 -*-

import ftputil
import re
import sys
from os import path
import os
import zipfile
from infix_operator import Infix
import time
import hashlib
from web_utils import getFileSha1


def path_join_func(dir, fname):
    return os.path.join(dir,fname)
pjoin = Infix(path_join_func)


def get_ext(fname):
    return path.splitext(fname)[-1].lower()


def psql(query:str, var=None):
    import psycopg2
    try:
        db2=psycopg2.connect(database='firmware', user='firmadyne',
                             password='firmadyne', host='127.0.0.1')
        cur = db2.cursor()
        cur.execute(query,var)
        if not query.startswith('SELECT'):
            db2.commit()
            return
        else:
            rows = cur.fetchall()
            return rows
    except psycopg2.Error as ex:
        print(ex, file=sys.stderr)
        db2.rollback()
        raise ex
    finally:
        db2.close()


localstor='./output/D-Link/ftp.dlink.eu/'
os.makedirs(localstor, exist_ok=True)


def download(fw_url):
    from urllib import request
    with request.urlopen(fw_url, timeout=60) as fin:
        from os import path
        fname = path.basename(fw_url)
        with open(localstor/pjoin/fname, 'wb') as fout:
            while True:
                buf = fin.read(64*1024)
                if len(buf)==0:
                    break
                fout.write(buf)


with open('dlink_ftp.dlink.eu_filelist.txt', 'w', encoding='utf8') as fout:
    with ftputil.FTPHost('ftp.dlink.eu', 'anonymous', '') as host:
        host.keep_alive()
        for root, dirs, fnames in host.walk('Products'):
            if '/driver_software' not in root:
                continue

            for fname in fnames:
                if get_ext(fname) not in ['.zip', '.bin', '.img', '.rar']:
                    continue
                fw_url = 'ftp://ftp.dlink.eu'/pjoin/root/pjoin/fname
                filesize = host.path.getsize(root/pjoin/fname)
                filemtime = host.path.getmtime(root/pjoin/fname)
                fout.write('\t'.join([fw_url, str(filesize), str(filemtime)]) + '\n')
                print('%(fw_url)s'%locals())
                # download(fw_url)

                # zf = zipfile.ZipFile(localstor/pjoin/fname)
                # zf.namelist()

                # psql('INSERT INTO image (filename, brand, fw_url) VALUES (%(fname)s, %(brand)s, %(fw_url)s )',
                #      locals())

