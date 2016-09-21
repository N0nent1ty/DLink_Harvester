#!/usr/bin/env python3
# -*- coding: utf8 -*-
import re
import csv
import os
import ftputil
from concurrent.futures import ProcessPoolExecutor
from web_utils import getFileSha1, getFileMd5


localstor='output/D-Link/files.dlink.com.au_2/'


def download(ftpurl):
    try:
        fname = ftpurl.split('/')[-1]
        if fname.lower() in ['thumbs.db']:
            return
        if fname.split('.')[-1].lower() in ['pdf','txt']:
            return
        with ftputil.FTPHost('files.dlink.com.au', 'anonymous', '') as host:
            fsize = host.path.getsize(ftpurl)
            fdate = host.path.getmtime(ftpurl)
            if os.path.isfile(localstor+fname) and os.path.getsize(localstor+fname)==fsize:
                print('%(fname)s already exists'%locals())
                return
            print('Start downloading %(ftpurl)s'%locals())
            host.download(ftpurl, localstor+fname)
            print('Finised downloading %(ftpurl)s'%locals())
            file_sha1 = getFileSha1(localstor+fname)
            file_md5 = getFileMd5(localstor+fname)
            with open('au_dlink_ftp_filelist.csv', 'a') as fout:
                cw = csv.writer(fout)
                cw.writerow([ftpurl, fsize, fdate, file_sha1, file_md5])
    except Exception as ex:
        print(ex)


def main():
    os.makedirs(localstor, exist_ok=True)
    with ProcessPoolExecutor() as executor:
        with ftputil.FTPHost('files.dlink.com.au', 'anonymous', '') as host:
            with open('au_dlink_ftp_filelist.csv', 'w') as fout:
                cw = csv.writer(fout)
                cw.writerow(["ftpurl", "fsize", "fdate", "file_sha1", "file_md5"])

            models = host.listdir('/Products/')
            for model in models:
                if not host.path.isdir('/Products/%(model)s'%locals()):
                    continue
                if not re.match(r'[A-Z]+', model, re.I):
                    continue
                revs = host.listdir('/Products/%(model)s/'%locals())
                for rev in revs:
                    if not re.match(r'REV_\w+', rev, re.I):
                        continue
                    try:
                        fwitems = host.listdir('/Products/%(model)s/%(rev)s/Firmware/'%locals())
                    except:
                        continue
                    try:
                        for fwitem in fwitems:
                            print('visiting /Products/%(model)s/%(rev)s/Firmware/%(fwitem)s/'%locals())
                            try:
                                fw_files = host.path.listdir('/Products/%(model)s/%(rev)s/Firmware/%(fwitem)s/'%locals())
                                for fw_file in fw_files:
                                    host.keep_alive()
                                    executor.submit(download, '/Products/%(model)s/%(rev)s/Firmware/%(fwitem)s/%(fw_file)s'%locals())
                            except:
                                if host.path.isfile('/Products/%(model)s/%(rev)s/Firmware/%(fwitem)s'%locals()):
                                    executor.submit(download,'/Products/%(model)s/%(rev)s/Firmware/%(fwitem)s'%locals())
                    except Exception as ex:
                        print(ex)


if __name__=="__main__":
    main()
