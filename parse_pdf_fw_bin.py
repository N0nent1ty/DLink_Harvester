from pdf_to_txt import convert
import zipfile
import os
import re
from datetime import datetime
import ipdb
import csv
from os import path


def zip_namelist(f):
    try:
        return zipfile.ZipFile(f).namelist()
    except zipfile.BadZipFile:
        return []


def getext(f):
    return os.path.splitext(f)[-1].lower()


def get_from_ftp_filelist(fname):
    with open('dlink_ftp.dlink.eu_filelist.txt') as fin:
        for line in fin:
            if fname in line:
                _,fsize,fdate = line.strip().split('\t')
                return int(fsize), datetime.fromtimestamp(float(fdate))


def parse_pdf(fname):
    zf = zipfile.ZipFile(fname)
    namelist = zf.namelist()
    try:
        pdf_fname = next(_ for _ in namelist if getext(_)=='.pdf')
    except StopIteration:
        pdf_fname = next(_ for _ in namelist if getext(_)=='.txt')
    if getext(pdf_fname)=='.pdf':
        txt = convert(zf.open(pdf_fname))
    else:
        txt = zf.open(pdf_fname).read().decode('latin2')
    txt = txt.splitlines()
    model, fw_ver, rev, rel_date = None,None,None,None
    for line in txt:
        line = line.strip()
        if not line:
            continue
        if model is None:
            model = line.split(' ')[0]

        try:
            valname, valval = line.split(':', maxsplit=1)
        except ValueError:
            continue
        valname = valname.lower()
        if valname=='firmware':
            fw_ver = re.search(r'v?(\d+(\.\d+)*)', valval, re.I)
            fw_ver = fw_ver.group(1)
        elif valname in ['hardware']:
            valval = re.sub(r'rev', '', valval, flags=re.I)
            rev = valval.strip('. ')
        elif valname in ['data','date']:
            try:
                rel_date = datetime.strptime(valval, '%Y/%m/%d')
            except ValueError:
                valval = re.sub(r'(\d{1,2})(th|rd|nd|st)', r'\1', valval, count=1, flags=re.I)
                valval = valval.replace(',', '').strip()
                for dateformat in ['%d %b %Y', '%d %B %Y', '%B %d %Y', '%b %d %Y', '%Y/%m/%d']:
                    try:
                        rel_date = datetime.strptime(valval, dateformat)
                        break
                    except ValueError:
                        pass
        if model and fw_ver and rev and rel_date:
            return model, fw_ver, rev, rel_date
    # if not fw_ver or not rev or not rel_date or not model:
    #    ipdb.set_trace()
    if not rel_date:
        _, rel_date = get_from_ftp_filelist(path.basename(fname))
    return model, fw_ver, rev, rel_date

localstor = 'output/D-Link/ftp.dlink.eu/'

def main():
    for fname in os.listdir(localstor):
        if not re.match(r'.*\.zip', fname, re.I):
            continue
        names = zip_namelist(localstor+fname)
        exts = {getext(_) for _ in names}
        if exts & {'.txt','.pdf'} and exts & {'.bin','.img','.had','hex'}:
            model, fw_ver, rev, rel_date = parse_pdf(localstor+fname)
            with open('fw_ver.csv', mode='a', encoding='utf8') as fout:
                cw = csv.writer(fout, dialect='excel')
                cw.writerow([fname, model, fw_ver, rel_date])
            print('%s\t%s\t%s\t%s\t%s'%(fname, model, fw_ver, rev, rel_date))


if __name__=='__main__':
    main()

