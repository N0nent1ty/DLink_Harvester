# -*- coding: utf8 -*-
import re
from urllib import parse
from pyquery import PyQuery as pq
import csv


def csvinit():
    with open('au_dlink_filelist.csv','w') as fout:
        cw = csv.writer(fout)
        cw.writerow(['model','rev','fw_ver','fw_url'])


def csvwrite(model,rev,fw_ver,fw_url):
    with open('au_dlink_filelist.csv','a') as fout:
        cw = csv.writer(fout)
        cw.writerow([model,rev,fw_ver,fw_url])


def parse_model_page(model):
    page_url = "http://support.dlink.com.au/Download/download.aspx?product=%s"%parse.quote(model)
    d = pq(url=page_url)

    fw_ver,rev=None,None
    isFirmware=False
    for td in d('div.SubHeading_red,div.SubHeading_blue,div.SubHeading,td.Download'):
        line = td.text_content().splitlines()[0].strip()
        if not line:
            continue
        # print('line="%s"'%line)
        if 'class' not in td.attrib:
            continue
        clazz = td.attrib['class']
        # print('clazz=="%s"'%clazz)
        if clazz=='SubHeading_red':
            m= re.search(r'REV\s*(\w+)', line, re.I)
            rev = m.group(1)
        elif clazz=='SubHeading_blue':
            isFirmware= line=='Firmware'
        elif clazz=='SubHeading':
            try:
                fw_ver = re.search(r'v\d+\.\d[0-9a-z\.]+',line,re.I).group(0)
            except AttributeError:
                pass
        elif clazz=='Download':
            if isFirmware:
                fw_url = td.cssselect('a')[0].attrib['href']
                csvwrite(model,rev,fw_ver,fw_url)
                print('"%s" "%s" "%s"  %s'%(model,rev,fw_ver,fw_url))


def crawl_models():
    prefix=[]
    suffix=[]
    with open('au_dlink_model_select.html') as fin:
        for line in fin:
            line = line.strip()
            if line.startswith('<option value="">Select</option>'):
                while True:
                    line = next(fin)
                    m = re.search(r'value="(\w+)"', line.strip(), re.I)
                    if not m:
                        break
                    prefix += [m.group(1)]
                suffix = [None for i in range(len(prefix))]
            elif line.startswith('group[0][0]=new Option("","")'):
                while True:
                    line = next(fin)
                    m= re.search(r'group\[(\d+)\]\[(\d+)\]=new\s+Option\("(\w+)',line.strip(), re.I)
                    if not m:
                        break
                    if m.group(3).strip().lower().startswith('select'):
                        continue
                    index = int(m.group(1))
                    index-=1
                    if suffix[index] is None:
                        suffix[index] = [m.group(3)]
                    else:
                        suffix[index] += [m.group(3)]
    for ipx, px in enumerate(prefix):
        for sx in suffix[ipx]:
            model='%s-%s'%(px,sx)
            print('model=%s'%model)
            parse_model_page(model)


def main():
    csvinit()
    crawl_models()


if __name__=='__main__':
    main()
