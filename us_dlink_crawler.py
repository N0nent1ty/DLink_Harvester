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
    m = re.search(r'\d+\.\d[0-9a-z\.]*', txt, re.I)
    if m:
        return m.group(0)
    else:
        ipdb.set_trace()
        return None


def csvinit():
    with open('us_dlink_filelist.csv', 'w') as fout:
        cw = csv.writer(fout)
        cw.writerow(['model', 'rev', 'fw_ver', 'fw_url', 'date'])


def csvwrite(row):
    with open('us_dlink_filelist.csv', 'a') as fout:
        cw = csv.writer(fout)
        cw.writerow(row)


def crawl_prod(prod_url, model):
    d = pq(url=prod_url)
    revs = [(_.attrib['value'], _.text_content().strip()) for _ in d('select#ddlHardWare option')]
    revs = [(int(revid),revname) for revid,revname in revs if revid]

    for revid,revname in revs:
        epoch = int(time.time()*1000)
        ajax_url='http://support.dlink.com/ajax/ajax.ashx?d=%(epoch)d&action=productfile&'\
            'lang=en-US&ver=%(revid)d&ac_id=1'%locals()
        ponse = requests.get(url=ajax_url, headers={'Referer':prod_url})
        for it in ponse.json()['item']:
            for fil in it['file']:
                if 'firmware' in fil['name'].lower():
                    fw_ver = extract_fw_ver(fil['name'])
                    date = extract_date(fil['date'])
                    print('%s %s %s %s %s'%(model, revname, fw_ver, fil['url'], date))
                    csvwrite([model,revname, fw_ver, fil['url'], date])


"http://support.dlink.com/ProductInfo.aspx?m=DWL-5000AP"
# no need ajax
# only one option in select.ddlHardWare

"http://support.dlink.com/ProductInfo.aspx?m=DFE-530TX%2B"
# need ajax get different version
# requests.Request('http://support.dlink.com/ajax/ajax.ashx?d=1473748848724&action=productfile&'\
#                 'lang=en-US&ver=1073&ac_id=1', headers=
#                 {'Referer':'http://support.dlink.com/ProductInfo.aspx?m=DFE-530TX%2B'})
# d = int(time.time()*1000)
# ver=1073
#  ```html
#     <select name="ddlHardWare" id="ddlHardWare" class="downloadddl">
#      <option value="">--Please select--</option>
#       <option value="1073">F</option>
#       <option value="1072">G</option>
# ```
# response is JSON format, like
#  In [48]: js['item'][0]['file'][1]['url']
#  Out[48]: 'ftp://FTP2.DLINK.COM/PRODUCTS/DFE-530TXPLUS/REVA/DFE-530TXPLUS_QIG_1.00_WIN95_EN.PDF'
#
#  In [49]: js['item'][0]['file'][1]['filetypename']
#  Out[49]: 'Quick Install Guide'
#
#  In [50]: js['item'][1]['file'][1]['filetypename']
#  Out[50]: 'User Manual'
#
#  In [52]: js['item'][2]['file'][0]['filetypename']
#  Out[52]: 'Datasheet'
#
#  In [53]: js['item'][3]['file'][0]['filetypename']
#  Out[53]: 'Driver'
#
"http://support.dlink.com/ajax/ajax.ashx?d=1473751407969&action=productfile&lang=en-US&ver=919&ac_id=1"
"http://support.dlink.com/ajax/ajax.ashx?d=1473751433239&action=productfile&lang=en-US&ver=920&ac_id=1"


def main():
    start_url="http://support.dlink.com/AllPro.aspx?type=all"
    d = pq(url=start_url)
    # all 442 models
    models = [_.text_content().strip() for _ in d('tr > td:nth-child(1) > .aRedirect')]
    csvinit()

    for model in models:
        prod_url = "http://support.dlink.com/ProductInfo.aspx?m=%s"%parse.quote(model)
        crawl_prod(prod_url, model)


if __name__=='__main__':
    main()
