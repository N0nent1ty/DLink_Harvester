#!/usr/bin/env python3
# -*- coding: utf8 -*-
import re
from urllib.parse import urljoin
from lxml import html
import requests
from dateutil.parser import parse as date_parse


def main():
    session = requests.Session()
    selectProduct(session, 'http://www.linksys.com/us/support/sitemap/')


def selectProduct(session, mainUrl):
    startProd = 46
    resp = session.get(mainUrl)
    tree = html.fromstring(resp.text)
    for iProd, prod in enumerate(tree.cssselect('.item>ul>li>a')[startProd:], startProd):
        print('prod=', prod.text_content())
        prodText = prod.text_content()
        href = prod.attrib['href']
        if 'E1000' in prodText:
            print(prodText)
        selectSupport(session, urljoin(resp.url, href))


def selectSupport(session, prodUrl):
    resp = session.get(prodUrl)
    tree = html.fromstring(resp.text)
    for iSupport, support in enumerate(tree.cssselect('.row>p>a')):
        print('support=', support.text_content().strip())
        if 'download' in support.text_content().lower():
            selectFile(session, urljoin(resp.url, support.attrib['href']))


def dom2text(dom, ignore_images=True, ignore_emphasis=True, ignore_tables=True):
    from lxml import etree
    import html2text
    htt = html2text.HTML2Text()
    htt.body_width = 0
    htt.ignore_images = ignore_images
    htt.ignore_emphasis = ignore_emphasis
    htt.ignore_tables = ignore_tables
    return htt.handle(etree.tostring(dom).decode())


def selectFile(session, fileUrl):
    resp = session.get(fileUrl)
    tree = html.fromstring(resp.text)
    contents = tree.cssselect('.article-accordian-content')
    accordians = tree.cssselect('.article-accordian')
    for iCont, content in enumerate(contents):
        hw_rev = accordians[iCont].text_content().strip()
        hw_rev = re.search(r'\d+(\.\d+)+', hw_rev).group(0)
        print('hw_rev=', hw_rev)
        # for h3 in content.cssselect('h3'):
        #     print('  h3=', h3.text_content().strip())
        text = dom2text(content)
        firmware = False
        for line in text.splitlines():
            if line.strip().startswith('#'):
                firmware = 'firmware' in line.lower()
            elif line.startswith('Ver'):
                fver = re.search(r'\d+(\.\d+)+', line).group(0)
            elif 'date' in line.lower():
                fdate = re.search(r'\d+/\d+\d+', line).group(0)
                fdate = date_parse(fdate)
            elif '[download]' in line.lower():
                furl = re.search(r'\((.+)\)', line).group(1)
                if firmware:
                    print('hw_rev, fver, fdate, furl ', hw_rev, fver, fdate, furl)


if __name__ == '__main__':
    main()

