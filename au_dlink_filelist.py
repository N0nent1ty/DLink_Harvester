from web_utils import getFileSha1, getFileMd5
import os
from urllib import parse
import csv


localstor='output/D-Link/files.dlink.com.au/'


def download_file(ftp_url):
    print('download_file "%s"'%ftp_url)
    fname = ftp_url.split('/')[-1]
    if os.path.exists(localstor+fname):
        print('aloready downloaded ',fname)
        if os.path.getsize(localstor+fname)>0:
            return localstor+fname
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


def main():
    with open('au_dlink_filelist2.csv','w') as fout:
        cw = csv.writer(fout)
        cw.writerow(['model','rev','fw_ver','fw_url','file_size','file_sha1','file_md5','file_date'])
        with open('au_dlink_filelist.csv','r') as fin:
            cr = csv.reader(fin)
            next(cr)
            for model, rev, fw_ver, fw_url in cr:
                if fw_url.split('.')[-1].lower() in ['pdf']:
                    continue
                fname = download_file(fw_url)
                file_sha1=getFileSha1(fname)
                file_md5=getFileMd5(fname)
                file_size=os.path.getsize(fname)
                file_date=get_ftp_date(fw_url)
                cw.writerow([model, rev, fw_ver, fw_url, file_size, file_sha1,file_md5,file_date])

if __name__=='__main__':
    main()
