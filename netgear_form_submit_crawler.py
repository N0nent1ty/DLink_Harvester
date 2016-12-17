import os
import csv
import re
import traceback
from concurrent.futures import ThreadPoolExecutor
from dateutil.parser import parse as parse_date
import requests
from lxml import html
from form_submit import form_submit
from web_utils import getFileSha1, getFileMd5
from urllib.parse import urlsplit
from contextlib import closing

visited = {}
executor = None
dlDir = './output/netgear/downloadcenter.netgear.com_form_submit/'
startCat=0
startFam=0
startProd=0
startFirmware=0
def main():
    global executor
    try:
        session = requests.Session()
        executor = ThreadPoolExecutor()
        os.makedirs(dlDir, exist_ok=True)
        url='http://downloadcenter.netgear.com'
        with open('netgear_filelist.csv', 'w') as fout:
            cw = csv.writer(fout)
            cw.writerow(['model', 'fw_ver', 'fileName', 'fw_url', 'fw_date', 'fileSize', 'sha1', 'md5'])
        response = session.get(url=url)
        root = html.fromstring(response.text)
        href = root.xpath(".//a[@id='ctl00_ctl00_ctl00_mainContent_localizedContent_bodyCenter_BasicSearchPanel_btnAdvancedSearch']/@href")
        href = strip_js(href[0])
        formdata = {"__EVENTTARGET": href}
        resp2 = form_submit(session, root, url,
                            "aspnetForm",
                            formdata,
                            {"Referer": url})
        walkCategories(session, resp2)
    except BaseException as ex:
        traceback.print_exc()
    finally:
        executor.shutdown(True)


def strip_js(url):
    return url.split('\'')[1]


def walkCategories(session, response):
    try:
        root = html.fromstring(response.text)
        url = response.url
        categories = root.xpath(".//select[@name='ctl00$ctl00$ctl00$mainContent$localizedContent$bodyCenter$adsPanel$lbProductCategory']/option")
        global startCat
        for iCat, category in enumerate(categories[startCat:], startCat):
            startCat=0
            rsrc = category.xpath("./@value")[0]
            text = category.xpath(".//text()")[0]
            print('Category="%s", iCat=%d'%(text, iCat))
            formdata= {"__EVENTTARGET": "ctl00$ctl00$ctl00$mainContent$localizedContent$bodyCenter$adsPanel$lbProductCategory",
                       "ctl00$ctl00$ctl00$mainContent$localizedContent$bodyCenter$adsPanel$lbProductCategory": rsrc,
                       "__ASYNCPOST:": "true"}
            resp2 = form_submit(session, root, url,
                                "aspnetForm",
                                formdata,
                                {"Referer": url})
            if not resp2:
                continue
            walkFamilies(session, resp2)
    except BaseException as ex:
        print('iCat=%d, cat="%s"'%(iCat, text))
        traceback.print_exc()


def walkFamilies(session, response):
    try:
        root = html.fromstring(response.text)
        url = response.url
        families = root.xpath("//select[@name='ctl00$ctl00$ctl00$mainContent$localizedContent$bodyCenter$adsPanel$lbProductFamily']/option")
        global startFam
        for iFam, family in enumerate(families[startFam:], startFam):
            startFam=0
            rsrc = family.xpath("./@value")[0]
            text = family.xpath(".//text()")[0]
            print('Family="%s", iFam=%d'%(text, iFam))
            formdata={"__EVENTTARGET": "ctl00$ctl00$ctl00$mainContent$localizedContent$bodyCenter$adsPanel$lbProductFamily",
                      "ctl00$ctl00$ctl00$mainContent$localizedContent$bodyCenter$adsPanel$lbProductFamily": rsrc,
                      "__ASYNCPOST:": "true"}
            resp2 = form_submit(session, root, url,
                                "aspnetForm",
                                formdata,
                                {"Referer": url})
            if not resp2:
                print('Ignored iFam=%d, family="%s"'%(iFam, text))
                import pdb; pdb.set_trace()
                continue
            walkProducts(session, resp2)
    except BaseException as ex:
        print('iFam=%d, family="%s"'%(iFam, text))
        traceback.print_exc()


def walkProducts(session, response):
    try:
        root = html.fromstring(response.text)
        products = root.xpath("//select[@name='ctl00$ctl00$ctl00$mainContent$localizedContent$bodyCenter$adsPanel$lbProduct']/option")
        url = response.url
        global startProd
        for iProd, product in enumerate(products[startProd:], startProd):
            startProd=0
            rsrc = product.xpath("./@value")[0]
            text = product.xpath(".//text()")[0]
            print('Product="%s", iProd=%d'%(text, iProd))
            formdata={"__EVENTTARGET": "ctl00$ctl00$ctl00$mainContent$localizedContent$bodyCenter$adsPanel$lbProduct",
                      "ctl00$ctl00$ctl00$mainContent$localizedContent$bodyCenter$adsPanel$lbProduct": rsrc,
                      "__ASYNCPOST:": "true"}
            resp2 = form_submit(session, root, url,
                                "aspnetForm",
                                formdata,
                                {"Referer": url})
            if not resp2:
                print('Ignored iProd=%d, product="%s"'%(iProd, text))
                continue
            walkFirmwares(resp2, product)
    except BaseException as ex:
        print('Error iProd=%d, product="%s"'%(iProd, text))
        traceback.print_exc()


def walkFirmwares(response, product):
    try:
        root = html.fromstring(response.text)
        firmwares = root.xpath("//div[@id='LargeFirmware']//a")
        for iFirm, firmware in enumerate(firmwares):
            text = firmware.xpath(".//text()")
            if "firmware" in " ".join(text).lower():
                # print('Firmware="%s", iFirmware=%d'%(text, iFirm))
                desc = text[0]
                href = firmware.xpath("./@data-durl")
                if not href:
                    href = firmware.xpath("./@href")
                url = href[0]
                model = product.xpath(".//text()")[0]
                print('model="%s", desc="%s", url=%s'%(model, desc, url))
                global executor, visited
                if url in visited:
                    continue
                visited[url] = (model,desc)
                executor.submit(download_file, model, desc, url)
    except BaseException as ex:
        traceback.print_exc()


def download_file(model, desc, fw_url):
    try:
        with closing(requests.get(url=fw_url, timeout=10, stream=True)) as resp:
            if 'Content-Length' in resp.headers:
                fileSize = int(resp.headers['Content-Length'])
                print('fileSize=', fileSize)
            else:
                fileSize=None
            try:
                fw_ver = re.search(r'\d+(\.\d+)+', desc).group(0)
            except AttributeError:
                fw_ver = ''
            fileName = os.path.basename(urlsplit(fw_url).path)
            print('fileName=', fileName)
            if not fileName:
                print('No fileName:, url=', fw_url)
                return
            if 'Last-Modified' in resp.headers:
                fw_date= resp.headers['Last-Modified']
                fw_date = parse_date(fw_date)
            else:
                fw_date = None
            if os.path.isfile(dlDir+fileName) \
                    and fileSize==os.path.getsize(dlDir+fileName):
                print('already downloaded: ', fileName)
            else:
                print('start downloading: ', fw_url)
                with open(dlDir+fileName+'.downloading', 'wb') as fout:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:  # filter out keep-alive new chunks
                            fout.write(chunk)
                try:
                    os.rename(dlDir+fileName+'.downloading', dlDir+fileName)
                except FileNotFoundError:
                    print('"%s" not found'%(dlDir+fileName+'.downloading'))
                print('finished downloading: ', fw_url)
            sha1 = getFileSha1(dlDir+fileName)
            md5 = getFileMd5(dlDir+fileName)
            if fileSize and os.path.getsize(dlDir+fileName)!=fileSize:
                print('Content-Length(%s) different to real fileSize %s' % (fileSize, os.path.getsize(dlDir+fileName)))
            fileSize = os.path.getsize(dlDir+fileName)
            with open('netgear_filelist.csv', 'a') as fout:
                cw = csv.writer(fout)
                cw.writerow([model, fw_ver, fileName, fw_url, fw_date, fileSize, sha1, md5])
    except BaseException as ex:
        traceback.print_exc()
        import pdb
        pdb.set_trace()


if __name__=='__main__':
    main()

