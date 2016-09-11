#!/usr/bin/env python3
# coding: utf-8
from pyquery import PyQuery as pq
import csv
from datetime import datetime
import re
# import ipdb


def extract_fw_ver(txt):
    m = re.search(r'\d+\.\d+[a-z]*\d*', txt, re.I)
    if m:
        return m.group(0)
    else:
        return None


fwdb=dict()


def parse_page(page_url, model):
    global fwdb
    # d = pq(url='http://www.dlink.com/uk/en/support/product/dir-300-wireless-g-router?revision=deu_reva#downloads')
    d = pq(url=page_url)
    options = d('select.download-select > option')
    for o in options:
        if 'Firmware' in o.attrib['data-tracking']:
            print('model="%s"'%model)
            fw_ver = extract_fw_ver(o.text_content())
            if fw_ver is None:
                # divs = [_.text_content().splitlines()[1].strip() for _ in d('div.dataTable')]
                # print('%s'%divs)
                continue
            print('fw_ver="%s"'%fw_ver)
            fw_url = o.attrib['data-url']
            new_file_date = o.attrib['data-date']
            if new_file_date!='-':
                for pat in ['%d/%m/%Y', '%d/%m/%y']:
                    try:
                        new_file_date = datetime.strptime(new_file_date, pat)
                        break
                    except ValueError:
                        continue
                assert type(new_file_date) is datetime
            else:
                new_file_date=None
            if fw_url not in fwdb:
                print('New fw_url: %s  fw_ver=%s'%(fw_url,fw_ver))
                fwdb[fw_url] = (model,fw_ver, -1,new_file_date, '','')
            else:
                model,fw_ver_old, file_size,file_date, file_sha1,file_md5 = fwdb[fw_url]
                if new_file_date is not None:
                    file_date = new_file_date
                fwdb[fw_url] = (model,fw_ver, file_size,file_date, file_sha1,file_md5)


def main():
    global fwdb
    fwdb={}
    with open('dlink_ftp.dlink.eu_filelist.csv', 'r') as fin:
        cr = csv.reader(fin, dialect='excel')
        next(cr)
        for fw_url, file_size, file_date, model_ls, file_sha1, file_md5 in cr:
            file_size=int(file_size)
            file_date = datetime.strptime(file_date, '%Y-%m-%d %H:%M:%S')
            model_ls = eval(model_ls)
            if not model_ls:
                model=''
            else:
                model=model_ls[0]
            fwdb[fw_url] = (model,'', file_size,file_date, file_sha1,file_md5)
    
    d = pq(url='http://www.dlink.com/uk/en/support/all-products?tab=all&po=true')
    for item in d('.support_popular_products > ul > li > a'):
        model = item.text_content().strip()
        parse_page(item.attrib['href'], model)
    # write to second CSV
    rows=[]
    for fw_url, value in fwdb.items():
        model,fw_ver, file_size,file_date, file_sha1,file_md5 = value
        rows.append((model,fw_ver, fw_url, file_size, file_date, file_sha1,file_md5))
    rows.sort(key=lambda r:(r[0].lower(), r[1].lower()))
    with open('dlink_ftp.dlink.eu_filelist2.csv', 'w') as fout:
        cw = csv.writer(fout)
        cw.writerow(['model', 'fw_ver', 'fw_url', 'file_size', 'file_date', 'file_sha1', 'file_md5'])
        cw.writerows(rows)


if __name__=='__main__':
    main()

