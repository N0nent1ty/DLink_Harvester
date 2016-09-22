from web_utils import getFileSha1
from web_utils import getFileMd5
import csv
import os
import urllib

localstor='output/D-Link/ftp2.dlink.com/'


def download_file(ftp_url):
    fname = ftp_url.split('/')[-1]
    if os.path.exists(localstor+fname):
        # print('dont overwrite:',fname)
        if os.path.getsize(localstor+fname)>0:
            return localstor+fname
    from urllib import request
    print('Download',ftp_url)
    with request.urlopen(ftp_url,timeout=30) as fin:
        with open(localstor+fname, 'wb') as fout:
            data = fin.read()
            fout.write(data)
            return localstor+fname


def main():
    with open('us_dlink_filelist.csv', 'r') as fin:
        cr = csv.reader(fin)
        next(cr)
        rows = [[model, rev, ver, url, date] for model, rev, ver, url, date in cr]
    for index,row in enumerate(rows):
        model,rev,fw_ver,ftp_url,date = row
        try:
            fname = download_file(ftp_url)
            sha1 = getFileSha1(fname)
            md5 = getFileMd5(fname)
            fsize = os.path.getsize(fname)
            rows[index] = [model,rev,fw_ver,ftp_url,date,fsize,sha1,md5]
        except urllib.error.URLError:
            print('Failed:', ftp_url)
            rows[index] = [model,rev,fw_ver,ftp_url,date,-1,'','']
        except ValueError:
            print('Failed wrong url "%s"'%ftp_url)
            rows[index] = [model,rev,fw_ver,ftp_url,date,-1,'','']
    with open('us_dlink_filelist2.csv', 'w') as fout:
        cw = csv.writer(fout)
        cw.writerow(['model','rev','fw_ver','ftp_url', 'date', 'size', 'sha1','md5'])
        cw.writerows(rows)


if __name__=='__main__':
    main()
