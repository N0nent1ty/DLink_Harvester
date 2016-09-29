#!/usr/bin/env python3
# coding: utf-8
from pyquery import PyQuery as pq
import re
from datetime import datetime
import csv
from urllib import parse


def csvinit():
    with open('jp_dlink_filelist.csv', 'w') as fout:
        cw = csv.writer(fout)
        cw.writerow(['model','fw_ver', 'fw_url', 'rel_date'])


def csvwrite(model, fw_ver, fw_url, rel_date):
    with open('jp_dlink_filelist.csv', 'a') as fout:
        cw = csv.writer(fout)
        cw.writerow([model,fw_ver, fw_url, rel_date])


def parse_prod(page_url):
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
                    rel_date = rel_date.replace('//', '/')
                    try:
                        rel_date = re.search('\d+/\d+/\d+', rel_date).group(0)
                        rel_date = datetime.strptime(rel_date, "%Y/%m/%d")
                    except (AttributeError,ValueError):
                        rel_date=None

                    csvwrite(model, fw_ver, fw_url, rel_date)
                    print('%s %s %s %s'%(model, fw_ver, fw_url, rel_date))


def crawl_serie(serie_url):
    d=pq(url=serie_url)
    prods = d('.productList td h3 a')
    for prod in enumerate(prods):
        model = prod.text_content().strip()
        print('model="%(model)s"'%locals())
        parse_prod(prod.attrib['href'])


root_url="https://www.dlink-jp.com/"


def crawl_cat(caturl):
    d=pq(url=caturl)
    series = d('dd>ul.clearfix>li>a')
    for serie in series:
        path = serie.attrib['href']
        print("serie=%(path)s"%locals())
        serie_url = parse.urljoin(root_url,path)
        crawl_serie(serie_url)


def main():
    csvinit()

    # d=pq(url=root_url)
    # cats = d("#gnav_01 .child p>a")
    # for cat in cats:
    #     path = cat.attrib['href']
    #     print("cat=%(path)s"%locals())
    #     caturl = parse.urljoin(root_url,path)
    #     crawl_cat(caturl)

    d=pq(url="http://www.dlink-jp.com/pog")
    prods = d(".pog_eos a")
    for prod in prods:
        model=prod.text_content().strip()
        print('model="%(model)s"'%locals())
        parse_prod(prod.attrib['href'])

    d=pq(url="http://dlink-jp.com/eos/")
    prods = d(".pog_eos a")
    for prod in prods:
        model=prod.text_content().strip()
        print('model="%(model)s"'%locals())
        parse_prod(prod.attrib['href'])


if __name__=='__main__':
    main()
