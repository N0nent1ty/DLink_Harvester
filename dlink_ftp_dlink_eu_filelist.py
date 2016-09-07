import csv
from datetime import datetime
from parse_pdf_fw_bin import get_model_from_ftp_url
from web_utils import getFileSha1
from web_utils import getFileMd5
from os import path


def main():
    with open('dlink_ftp.dlink.eu_filelist.csv', 'w') as fout:
        cw = csv.writer(fout, dialect='excel')
        cw.writerow(['ftp_url', 'file_size', 'file_date', 'model', 'file_sha1', 'file_md5'])
        with open('dlink_ftp.dlink.eu_filelist.txt', 'r') as fin:
            for line in fin:
                line=line.strip()
                if not line:
                    continue
                ftpurl, fsize, fdate = line.split('\t', 2)
                fdate = datetime.fromtimestamp(float(fdate))
                fname = 'output/D-Link/ftp.dlink.eu/' + ftpurl.split('/')[-1]
                sha1 = getFileSha1(fname)
                md5 = getFileMd5(fname)
                fsize = path.getsize(fname)
                model = get_model_from_ftp_url(ftpurl)
                cw.writerow([ftpurl, fsize, fdate, model,sha1,md5])
                print('%s,%s,%s,%s'%(ftpurl,fsize,fdate,model))


if __name__=="__main__":
    main()
