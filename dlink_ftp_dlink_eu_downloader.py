import os


def path_join_func(dir, fname):
    from os import path
    return path.join(dir,fname)
from infix_operator import Infix
pjoin = Infix(path_join_func)


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


with open('dlink_ftp.dlink.eu_filelist.txt', 'r', encoding='utf8') as fin:
    for line in fin:
        fw_url, fw_size, fw_mtime = line.split('\t')
        print('download', fw_url)
        download(fw_url)

