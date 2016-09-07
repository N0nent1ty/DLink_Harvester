from pdf_to_txt import convert
import zipfile
import os
import re
from datetime import datetime
import csv
from os import path
import sys
from infix_operator import Infix


def regex_like_func(text, pattern):
    m = re.match(pattern, text, re.I)
    if m is None:
        return None
    assert m.group(0)
    return m.group(0)
like = Infix(regex_like_func)


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
                fw_url, fsize, fdate = line.strip().split('\t')
                return fw_url, int(fsize), datetime.fromtimestamp(float(fdate))

ptn_ignores=['driver_software', '@?archive', 'Products', 'ftp', 'add-?on', 'old$', 'rev_', 'spain$', 'Win2000$',
             'wireless fix', 'Treiber', '[A-Z]_[0-9a-z]+', 'shareport', '.+_fw_', 'chrome', '[a-z]{1,3}$',
             'd-link', 'd-viewcam', '.*ap-?array', '.+-.*arraytool$', '.+ device', '.+-apmii$']
ptn_prefix=r'(go-[a-z]{2,3}|[a-z]{1,4})'
ptn_hyphen='-'
ptn_suffix=r'[a-z]{0,2}\d{0,4}[a-z]{0,3}\d?(\+|[a-z]{1,4}|-\d{1,2}[a-z]{0,2})?'


def is_dlink_model_name(name):
    if any(name /like/ _ for _ in ptn_ignores):
        return 0
    if '-' not in name:
        return 10
    if any(_ in name for _ in "~`!@#$%^&*=_\\|[]{}'\":;?/,.<>"):
        return 5
    if ' ' in name:
        return 20  # need to split

    prefix = name/like/ptn_prefix
    if prefix is None:
        return 25  # not recognized model name
    name1 = name[len(prefix):]
    if not name1/like/ptn_hyphen:
        return 0
    name2 = name1[len(name1/like/ptn_hyphen):]
    if len(name2)==0:
        return 25
    suffix = name2/like/ptn_suffix
    if not suffix:
        return 10
    name3 = name2[len(suffix):]
    if len(name3)==0:
        return 100
    return 90


def is_partial_dlink_model_name(name):
    if name /like/ ptn_suffix:
        return True
    else:
        return False


def test_possible_dlink_models():
    with open('possible_dlink_models.txt', encoding='utf8') as fin:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            score = is_dlink_model_name(line)
            if score<100:
                print(line, score)


def extract_dlink_model_name(text):
    comps = text.split()
    for i,comp in enumerate(comps):
        if not is_dlink_model_name(comps):
            continue
        if is_partial_dlink_model_name(comps):
            yield comps[i-1], comp
        yield comp


def get_model_from_ftp_url(ftp_url):
    ftp_url = ftp_url.replace('ftp://ftp.dlink.eu/Products/', '')
    comps = ftp_url.split('/')[::-1]
    fname=comps[0].split('.')[0]
    comps = comps[1:]
    for comp in comps:
        if any(comp /like/ _ for _ in ptn_ignores+[re.escape(fname)]):
            continue
        elif '&' in comp:
            return [_.strip() for _ in comp.split('&')]
        elif ' ' in comp:
            mdls = comp.split(' ')
            if '-' not in mdls[0]:
                continue
            if mdls[1] /like/ ptn_suffix:
                mdl2 = mdls[0].split('-')[0] + mdls[1]
                return [mdls[0], mdl2]
        else:
            return [comp]
    return []


def collect_model():
    models = set()
    with open('dlink_ftp.dlink.eu_filelist.txt', encoding='utf8') as fin:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            ftp_url, *_ = line.split('\t')
            models |= set(_.lower() for _ in get_model_from_ftp_url(ftp_url))
    models = list(models)
    models.sort()
    print('\n'.join(models))


def parse_pdf(fname):
    fw_url, fw_size, rel_date = get_from_ftp_filelist(path.basename(fname))
    print('process ', path.basename(fname))
    zf = zipfile.ZipFile(fname)
    namelist = zf.namelist()
    try:
        pdf_fname = next(_ for _ in namelist if getext(_) == '.pdf')
    except StopIteration:
        pdf_fname= next(_ for _ in namelist if getext(_)=='.txt')
    model, fw_ver, rev = None,None,None
    print('pdf_name:', pdf_fname)
    try:
        if getext(pdf_fname)=='.pdf':
            txt = convert(zf.open(pdf_fname))
        else:
            txt = zf.open(pdf_fname).read().decode('latin2')
    except zipfile.BadZipFile:
        return model, fw_ver, rev, rel_date, fw_size
    txt = txt.splitlines()
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
        if fw_ver and rev:
            break
    return model, fw_ver, rev, rel_date, fw_size


localstor = 'output/D-Link/ftp.dlink.eu/'


def proc(fname):
    names = zip_namelist(fname)
    exts = {getext(_) for _ in names}
    if exts & {'.txt','.pdf'} and exts & {'.bin','.img','.had','hex'}:
        model, fw_ver, rev, rel_date, fw_size = parse_pdf(fname)
        with open('fw_ver.csv', mode='a', encoding='utf8') as fout:
            cw = csv.writer(fout, dialect='excel')
            cw.writerow([fname, model, fw_ver, rel_date, fw_size])
        print('%(fname)s\t%(model)s\t%(fw_ver)s\t%(rev)s\t%(rel_date)s\t%(fw_size)s'%locals())


def main():
    if len(sys.argv)>1:
        fname = sys.argv[1]
        proc(fname)
    else:
        for fname in os.listdir(localstor):
            if not re.match(r'.*\.zip', fname, re.I):
                continue
            proc(localstor + fname)


if __name__=='__main__':
    test_possible_dlink_models()

