#!/usr/bin/env python3
# -*- coding: utf8 -*-
import csv
import re
import os
from urllib import request
from urllib import parse
from concurrent import futures
from pyquery import PyQuery as pq
import ftputil
from web_utils import getFileSha1, getFileMd5


executor=None
localstor='output/D-Link/files.dlink.com.au/'


def download(model, rev, fw_ver, fw_url):
    try:
        fname = fw_url.split('/')[-1]

        def epilog(fsize, fdate):
            sha1 = getFileSha1(localstor+fname)
            md5 = getFileMd5(localstor+fname)
            with open('au_dlink_filelist.csv', 'a') as fout:
                cw = csv.writer(fout)
                cw.writerow([model, rev, fw_ver, fw_url, fsize, fdate, sha1, md5])
            return

        if fname.lower() in ['thumbs.db']:
            return
        if fname.split('.')[-1].lower() in ['pdf','txt']:
            return
        from urllib import parse
        fw_path = parse.urlsplit(fw_url).path
        netloc = parse.urlsplit(fw_url).netloc
        with ftputil.FTPHost(netloc, 'anonymous', '') as host:
            fsize = host.path.getsize(fw_path)
            fdate = host.path.getmtime(fw_path)
            if os.path.isfile(localstor+fname) and os.path.getsize(localstor+fname)==fsize:
                print('%(fname)s already exists'%locals())
                epilog(fsize,fdate)
                return
            print('Start downloading %(fw_url)s'%locals())
            host.download(fw_path, localstor+fname)
            print('Finised downloading %(fw_url)s'%locals())
            epilog(fsize,fdate)
            return
    except Exception as ex:
        print(ex)


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
                print('"%s" "%s" "%s"  %s'%(model,rev,fw_ver,fw_url))
                global executor
                executor.submit(download, model, rev, fw_ver, fw_url)


def crawl_models():
    prefix=[]
    suffix=[]
    with request.urlopen('http://faq.dlink.com.au/supportfaq/BrainTree.aspx?Model=', timeout=60) as fin:
        content = fin.read().decode('utf8').splitlines()
    fin = iter(content)
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
    with open('au_dlink_filelist.csv','w') as fout:
        cw = csv.writer(fout)
        cw.writerow(['model','rev','fw_ver','fw_url', 'fsize', 'fdate', 'sha1', 'md5'])
    os.makedirs(localstor, exist_ok=True)
    global executor
    executor=futures.ThreadPoolExecutor()
    crawl_models()
    print('wait for Executor shutdown')
    executor.shutdown(True)


if __name__=='__main__':
    main()
