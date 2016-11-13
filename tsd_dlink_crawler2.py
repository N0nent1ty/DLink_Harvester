#!/usr/bin/env python3
# -*- coding:utf8 -*-
import re
import os
import csv
from concurrent import futures
import requests
from lxml import html
from os.path import splitext
from datetime import datetime
import traceback
import socket
from web_utils import getFileSha1, getFileMd5


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


def download(session, url, model, filename, fw_ver, fdate):
    from urllib import parse
    fname = filename
    try:
        doccont = session.get(
            url=url,
            headers={'Referer':'http://tsd.dlink.com.tw/downloads2008detailgo.asp',
                     'Upgrade-Insecure-Requests':'1'}, stream=True)
        fw_url = doccont.url
        print('fw_url=', fw_url)
        docParams = parse.parse_qs(parse.urlsplit(doccont.url).query)
        print('docParams=', docParams)
        if 'fileName' in docParams:
            fname = docParams['fileName'][0]
        else:
            fname = os.path.basename(parse.urlsplit(fw_url).path)
        if 'fileSize' in docParams:
            fsize = int(float(docParams['fileSize'][0]))
            print('fsize=', fsize)
        if 'Content-Length' in doccont.headers:
            fsize = int(doccont.headers['Content-Length'])
        if 'Content-Disposition' in doccont.headers:
            print('Content-Disposition=', doccont.headers['Content-Disposition'])
            fname = doccont.headers['Content-Disposition'].split(';', 1)[1].split('=', 1)[1]
        if 'fsize' in locals():
            if os.path.isfile(localstor+fname) and os.path.getsize(localstor+fname)==fsize:
                print('"%s" already exists'%(localstor+fname))
                return
        with open(localstor + fname, 'wb') as fout:
            for chunk in doccont.iter_content(4096):
                fout.write(chunk)
        fsize = os.path.getsize(localstor + fname)
        sha1 = getFileSha1(localstor + fname)
        md5 = getFileMd5(localstor + fname)
        with open('tsd_dlink_filelist.csv', 'a') as fout:
            cw = csv.writer(fout)
            cw.writerow([model, '', fw_ver, fw_url, fdate, fsize, sha1, md5])
    except socket.timeout:
        print('timeout error')
        return
    except requests.exceptions.Timeout as ex:
        traceback.print_exc()
        print('timeoute error')
        return
    except BaseException as ex:
        traceback.print_exc()
        print(ex)
        return


def selectModel(pfx, sfx):
    try:
        model='%s-%s'%(pfx, sfx)
        print('Model=', model)
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
        # doctypes = tree.xpath(".//tr[@id='rsq']/td[1]/text()")
        docnames = tree.xpath(".//tr[@id='rsq']/td[2]/text()")
        doc_dwns = tree.xpath(".//tr[@id='rsq']/@onclick")
        for irow, docname in enumerate(docnames):
            doctype = docname.split(':')[0].strip().lower()
            if doctype =='firmware':
                docuSno, docuSource = re.search(
                    r"dwn\('(.+?)',\s*'(.+?)'\)", doc_dwns[irow]).groups()
                details = session.post(
                    url='http://tsd.dlink.com.tw/downloads2008detailgo.asp',
                    data={"Enter":"OK", "ModelCategory":"0", "ModelCategory_":pfx,
                          "ModelSno":"0", "ModelSno_":sfx,
                          "ModelVer":"", "Model_Sno":"",
                          "docuSno":docuSno, "docuSource":docuSource},
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
                        global executor
                        executor.submit(download, session,
                                        'http://tsd.dlink.com.tw/asp/get_file.asp?sno=%s'%sno,
                                        model, filename, fw_ver, fdate)
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
    startI = next(i for i,sp in enumerate(models) if sp[0]=='DIR' and sp[1]=='845L')
    for model in models[startI:]:
        pfx,sfx = model[0], model[1]
        selectModel(pfx, sfx)

    print('wait for Executor shutdown')
    executor.shutdown(True)


if __name__=='__main__':
    main()

