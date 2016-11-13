#!/usr/bin/env python3
# -*- coding:utf8 -*-
import re
import os
import csv
from concurrent import futures
import requests
from lxml import html
from os.path import splitext
import hashlib
from datetime import datetime
import traceback
import socket


localstor='output/D-Link/tsd.dlink.com.tw/'
executor=None


def parse_models():
    models = []
    fin = requests.get('http://tsd.dlink.com.tw/scripts/ModelNameSelect2008.js')
    htmlines = fin.text.splitlines()
    for line in htmlines:
        m = re.search(r"\(k\s*==\s*'(.+?)'\)", line)
        if m:
            prefix = m.group(1)
        suffixs = re.findall(r"sl\.options\[i\]\.text='(.+?)'", line)
        suffixs = [_ for _ in suffixs if not _.lower().startswith('select')]
        models += [(prefix, sfx) for sfx in suffixs]

    return models


def parse_fw_ver(txt):
    try:
        m = re.search(r'v(\d+(\.\d+)+)', txt, re.I)
        if not m:
            return ""
        fw_ver = m.group(1)
        return fw_ver
    except BaseException as ex:
        traceback.print_exc()
        print(ex)


def parse_date(txt):
    try:
        return datetime.strptime(txt.strip(), '%Y/%m/%d')
    except BaseException as ex:
        traceback.print_exc()
        print(ex)


firmware_extnames = ['.bin', '.zip', '.had', '.rar', '.rmt', '.swap', '.img',
                     '.bix', '.hex', '.stk', '.bz2', '.tar', '.opr', '', '.exe']


def selectModel(pfx, sfx):
    try:
        print('Model=%s - %s'%(pfx,sfx))
        session = requests.Session()
        session.get('http://tsd.dlink.com.tw/')
        docs = session.post(
            url='http://tsd.dlink.com.tw/downloads2008detail.asp',
            data={'Enter':"OK", 'ModelCategory':pfx, 'ModelSno':sfx,
                  'ModelCategory_home':pfx, 'ModelSno_home':sfx},
            headers={'Referer':"http://tsd.dlink.com.tw/",
                     'Upgrade-Insecure-Requests':"1"}, timeout=30)
        tree = html.fromstring(docs.text)
        print('%s'% tree.xpath(".//tr[@id='rsq']/td/text()"))
        doctypes = tree.xpath(".//tr[@id='rsq']/td[1]/text()")
        # docnames = tree.xpath(".//tr[@id='rsq']/td[2]/text()")
        # docsizes = tree.xpath(".//tr[@id='rsq']/td[3]/text()")
        doc_dwns = tree.xpath(".//tr[@id='rsq']/@onclick")
        for irow, doctype in enumerate(doctypes):
            if doctype.lower().strip() =='firmware':
                docuSno, docuSource = re.search(
                    r"dwn\('(.+?)',\s*'(.+?)'\)", doc_dwns[irow]).groups()
                details = session.post(
                    url='http://tsd.dlink.com.tw/downloads2008detailgo.asp',
                    data={"Enter":"OK", "ModelCategory":"0", "ModelCategory_":pfx,
                          "ModelSno":"0", "ModelSno_":sfx,
                          "ModelVer":"", "Model_Sno":"",
                          "docuSno":docuSno, "docuSource":"1"},
                    headers={"Referer":"http://tsd.dlink.com.tw/downloads2008detail.asp",
                             "Upgrade-Insecure-Requests":"1"}, timeout=30)
                tree = html.fromstring(details.text)
                details = tree.xpath('.//td[@class="MdDclist12"]/text()')
                print('details = %r'%details)
                fw_ver = parse_fw_ver(details[1])
                fdate = parse_date(details[3])
                filenames = tree.xpath(".//*[@class='fn9']/text()")
                file_hrefs = tree.xpath(".//*[@class='fn9']/@href")
                print('filenames=', filenames)
                for jfil, filename in enumerate(filenames):
                    print('filename[%d]=%s'%(jfil, filename))
                    if splitext(filename)[-1].lower() not in ['.doc', '.pdf', '.txt', '.xls', '.docx']:
                        sno = re.search(r"dnn\('(.+?)'\)", file_hrefs[jfil]).group(1)
                        print('sno=', sno)
                        try:
                            doccont = session.get(
                                url='http://tsd.dlink.com.tw/asp/get_file.asp?sno=%s'%sno,
                                headers={'Referer':'http://tsd.dlink.com.tw/downloads2008detailgo.asp',
                                         'Upgrade-Insecure-Requests':'1'})
                            fw_url = doccont.url
                            print('fw_url=', fw_url)
                            if 'Content-Length' in doccont.headers:
                                print('Content-Length=',doccont.headers['Content-Length'])
                            if 'Content-Disposition' in doccont.headers:
                                print('Content-Disposition=', doccont.headers['Content-Disposition'])
                                fname = doccont.headers['Content-Disposition'].split(';', 1)[1].split('=', 1)[1]
                            if 'fname' not in locals():
                                from urllib import parse
                                fname = os.path.basename(parse.urlsplit(fw_url).path)
                            with open(localstor + fname, 'wb') as fout:
                                fout.write(doccont.content)
                        except socket.timeout:
                            print('timeout error')
                            continue
                        except requests.exceptions.Timeout as ex:
                            traceback.print_exc()
                            print('timeoute error')
                            continue
                        fsize = len(doccont.content)
                        sha1 = hashlib.sha1(doccont.content).hexdigest()
                        md5 = hashlib.md5(doccont.content).hexdigest()
                        with open('tsd_dlink_filelist.csv', 'a') as fout:
                            cw = csv.writer(fout)
                            model='%s-%s'%(pfx, sfx)
                            cw.writerow([model, '', fw_ver, fw_url, fdate, fsize, sha1, md5])
    except BaseException as ex:
        traceback.print_exc()


def main():
    os.makedirs(localstor, exist_ok=True)
    with open('tsd_dlink_filelist.csv', 'w') as fout:
        cw = csv.writer(fout)
        cw.writerow(['model', 'rev', 'fw_ver', 'fw_url', 'date', 'fsize', 'sha1', 'md5'])
    global executor
    executor = futures.ThreadPoolExecutor()

    models = parse_models()
    startI = next(i for i,sp in enumerate(models) if sp[0]=='DBT' and sp[1]=='120')
    for model in models[startI:]:
        pfx,sfx = model[0], model[1]
        selectModel(pfx, sfx)

    print('wait for Executor shutdown')
    executor.shutdown(True)


if __name__=='__main__':
    main()
