#!/usr/bin/env python3
# coding: utf-8
from pyquery import PyQuery as pq
import re
from datetime import datetime
import csv


def csvinit():
    with open('jp_dlink_filelist.csv', 'w') as fout:
        cw = csv.writer(fout)
        cw.writerow(['model','fw_ver', 'fw_url', 'rel_date'])


def csvwrite(model, fw_ver, fw_url, rel_date):
    with open('jp_dlink_filelist.csv', 'a') as fout:
        cw = csv.writer(fout)
        cw.writerow([model,fw_ver, fw_url, rel_date])


def parse_page(page_url):
    d = pq(url=page_url)
    model = d('.entry-title>strong')[0].text_content()
    items = d('h4,h5,li')
    for index, item in enumerate(items):
        if 'id' in item.attrib and item.attrib['id']=='product_firmware':
            for li in items[index+1:]:
                if li.tag=='h4':
                    break
                txt = li.text_content().strip()
                if txt.startswith('バージョン'):
                    fw_ver = re.search(r'R\d+[\.a-z0-9]+', txt, re.I).group(0)
                if li.cssselect('div.name strong') and \
                        li.cssselect('div.name strong')[0].text_content().startswith('ファームウェア'):
                    fw_url = li.cssselect('a')[0].attrib['href']
                    rel_date = li.cssselect('div.date')[0].text_content().strip()
                    rel_date = re.search('\d+/\d+/\d+', rel_date).group(0)
                    rel_date = datetime.strptime(rel_date, "%Y/%m/%d")
                    csvwrite(model, fw_ver, fw_url, rel_date)
                    print('%s %s %s'%(fw_ver, fw_url, rel_date))


def main():
    parse_page("http://www.dlink-jp.com/product/des-3200-28-t-h-w-c1")

if __name__=='__main__':
    main()
