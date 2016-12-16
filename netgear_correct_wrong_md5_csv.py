import csv
from web_utils import getFileMd5
from web_utils import getFileSha1
import os

def parse_date(s):
    try:
        from dateutil.parser import parse as parse
        return parse(s)
    except:
        return None

def main():
    dlDir='./output/netgear/downloadcenter.netgear.com_form_submit/'
    with open('netgear_filelist.csv', 'r') as fin:
        cr = csv.reader(fin)
        next(cr)
        rows = [(model, fver, fname, furl,parse_date(fdate), int(fsize), sha1, md5)
                for model, fver, fname, furl, fdate, fsize, sha1, md5 in cr]

    with open('netgear_filelist2.csv', 'w') as fout:
        cw = csv.writer(fout)
        cw.writerow(['model', 'fw_ver', 'fileName', 'fw_url', 'fw_data', 'fileSize', 'sha1', 'md5'])
        for model, fver, fname, furl, fdate, fsize, sha1, md5 in rows:
            fsizeC = os.path.getsize(dlDir+fname)
            sha1C = getFileSha1(dlDir+fname)
            md5C = getFileMd5(dlDir+fname)
            if fsizeC != fsize:
                print('"%s" wrong fileSize(%s), correct= %s'%(fname, fsize, fsizeC))
            elif sha1C != sha1:
                print('"%s" wrong sha1(%s), correct= %s'%(fname, sha1, sha1C))
            elif md5C != md5:
                print('"%s" wrong md5(%s), correct= %s'%(fname, md5, md5C))
            cw.writerow([model, fver, fname, furl, fdate, fsizeC, sha1C, md5C])

if __name__=='__main__':
    main()

