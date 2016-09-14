# -*- coding:utf8 -*-
from urllib import parse
from pyquery import PyQuery as pq
import requests
import time
# import json
from datetime import datetime
import re
import ipdb
# import traceback
import csv


def extract_date(txt):
    for pat in ['%m/%d/%y', '%Y/%m/%d']:
        try:
            return datetime.strptime(txt, pat)
        except ValueError:
            continue
    return None


def extract_fw_ver(txt):
    m = re.search(r'\((.+)\)', txt, re.I)
    if m:
        m2 = re.search(r'[0-9a-z\.]+', m.group(1), re.I)
        return m2.group(0)
    else:
        ipdb.set_trace()
        m = re.search(r'\d+\.\d[0-9a-z\.]*', txt, re.I)
        return None


def csvinit():
    with open('ca_dlink_filelist.csv', 'w') as fout:
        cw = csv.writer(fout)
        cw.writerow(['model', 'rev', 'fw_ver', 'fw_url', 'date'])


def csvwrite(row):
    with open('ca_dlink_filelist.csv', 'a') as fout:
        cw = csv.writer(fout)
        cw.writerow(row)


def crawl_prod(prod_url, model):
    d = pq(url=prod_url)
    revs = [(_.attrib['value'], _.text_content().strip()) for _ in d('select#ddlHardWare option')]
    revs = [(int(revid),revname) for revid,revname in revs if revid]

    for revid,revname in revs:
        epoch = int(time.time()*1000)
        ajax_url='http://support.dlink.ca/ajax/ajax.ashx?'\
            'd=%(epoch)d&action=productfile&lang=en-US&ver=%(revid)d&ac_id=1'\
            %locals()
        ponse = requests.get(url=ajax_url, headers={'Referer':prod_url})
        for it in ponse.json()['item']:
            for fil in it['file']:
                if 'firmware' in fil['name'].lower():
                    fw_ver = extract_fw_ver(fil['name'])
                    date = extract_date(fil['date'])
                    print('%s %s %s %s %s'%(model, revname, fw_ver, fil['url'], date))
                    csvwrite([model,revname, fw_ver, fil['url'], date])


def main():
    start_url='http://support.dlink.ca/AllPro.aspx?type=all'
    d = pq(url=start_url)
    # all 442 models
    models = [_.text_content().strip() for _ in d('tr > td:nth-child(1) > .aRedirect')]
    csvinit()

    for model in models:
        prod_url = 'http://support.dlink.ca/ProductInfo.aspx?m=%s'%parse.quote(model)
        crawl_prod(prod_url, model)


if __name__=='__main__':
    main()
