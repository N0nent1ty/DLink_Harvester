#!/usr/bin/env python3
# coding: utf-8
import harvest_utils
from harvest_utils import waitClickable, waitText, getElems, \
    getElemText, dumpSnapshot, waitElem, getText
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.remote.webelement import WebElement # noqa
from selenium.common.exceptions import NoSuchElementException # noqa
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import StaleElementReferenceException # noqa
from selenium.common.exceptions import WebDriverException # noqa
import time
import sys
import csv
import re
import os
import requests
import dateutil # noqa
from dateutil.parser import parse as parse_date
import urllib
import traceback
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from web_utils import uprint, getFileSha1, getFileMd5
# import pdb


dlDir= './output/netgear/downloadcenter.netgear.com/'


catSelCss="#ctl00_ctl00_ctl00_mainContent_localizedContent_bodyCenter_adsPanel_lbProductCategory"
famSelCss="#ctl00_ctl00_ctl00_mainContent_localizedContent_bodyCenter_adsPanel_lbProductFamily"
prdSelCss="#ctl00_ctl00_ctl00_mainContent_localizedContent_bodyCenter_adsPanel_lbProduct"
catWaitingCss="#ctl00_ctl00_ctl00_mainContent_localizedContent_bodyCenter_adsPanel_updProgress > div > img"
famWaitingCss="#ctl00_ctl00_ctl00_mainContent_localizedContent_bodyCenter_adsPanel_UpdateProgress1 > div > img"
prdWaitingCss='#ctl00_ctl00_ctl00_mainContent_localizedContent_bodyCenter_adsPanel_upProgProductLoader > div > img'
numResultsCss='#ctl00_ctl00_ctl00_mainContent_localizedContent_bodyCenter_adsPanel_lvwAllDownload_lblAllDownloadResult'


def download_file(model, fileName, fw_url):
    try:
        resp = requests.get(url=fw_url, stream=True)
        if 'Content-Length' in resp.headers:
            fileSize = int(resp.headers['Content-Length'])
            print('fileSize=', fileSize)
        else:
            fileSize=None
        try:
            fw_ver = re.search(r'\d+(\.\d+)+', fileName).group(0)
        except AttributeError:
            fw_ver = ''
        fileName= os.path.basename(urllib.parse.urlsplit(fw_url).path)
        print('fileName=', fileName)
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
                for chunk in resp.iter_content(8192):
                    fout.write(chunk)
            os.rename(dlDir+fileName+'.downloading', dlDir+fileName)
            print('finished downloading: ', fw_url)
        sha1 = getFileSha1(dlDir+fileName)
        md5 = getFileMd5(dlDir+fileName)
        fileSize = os.path.getsize(dlDir+fileName)
        with open('netgear_filelist.csv', 'a') as fout:
            cw = csv.writer(fout)
            cw.writerow([model, fw_ver, fileName, fw_url, fw_date, fileSize, sha1, md5])
    except BaseException as ex:
        traceback.print_exc()


def waitTextChanged(css:str,oldText:str, timeOut=60.0, pollFreq=0.5) -> str:
    begin = time.time()
    while (time.time() - begin) < timeOut:
        newText = getText(css)
        if newText != oldText:
            return newText
        else:
            time.sleep(pollFreq)
    raise TimeoutException('[waitTextChanged] text Unchanged="%s"'%(oldText))


def main1(catIdx, famIdx, prdIdx, executor):
    startCatIdx, startFamIdx, startPrdIdx = catIdx, famIdx, prdIdx
    driver = webdriver.PhantomJS()
    harvest_utils.driver = driver
    driver.get('http://downloadcenter.netgear.com/')
    # click DrillDown
    waitClickable('#ctl00_ctl00_ctl00_mainContent_localizedContent_bodyCenter'
                  '_BasicSearchPanel_btnAdvancedSearch').click()
    #
    # wait Page2
    try:
        catSel = Select(waitClickable(catSelCss))
        numCat = len(catSel.options)
        for catIdx in range(startCatIdx, numCat):
            catSel = Select(waitClickable(catSelCss))
            print('catIdx=', catIdx)
            startCatIdx = 0
            catTxt = catSel.options[catIdx].text
            uprint('catTxt= '+ catTxt)
            oldText = getText(famSelCss)
            catSel.select_by_index(catIdx)
            waitTextChanged(famSelCss, oldText)
            famSel = Select(waitClickable(famSelCss))
            numFam = len(famSel.options)
            for famIdx in range(startFamIdx,numFam):
                famSel = Select(waitClickable(famSelCss))
                print('famIdx=', famIdx)
                startFamIdx = 0
                famTxt = famSel.options[famIdx].text
                uprint('famTxt= '+famTxt)
                oldText = getText(prdSelCss)
                famSel.select_by_index(famIdx)
                waitTextChanged(prdSelCss, oldText)
                prdSel = Select(waitClickable(prdSelCss))
                numPrd = len(prdSel.options)
                for prdIdx in range(startPrdIdx,numPrd):
                    prdSel = Select(waitClickable(prdSelCss))
                    startPrdIdx=0
                    print("catIdx=%d, famIdx=%d, prdIdx=%d"%(catIdx,famIdx,prdIdx))
                    prdTxt = prdSel.options[prdIdx].text
                    uprint('cat,fam,prd=("%s","%s","%s")'%(catTxt,famTxt,prdTxt))
                    prdWaiting = waitElem(prdWaitingCss)
                    prdSel.select_by_index(prdIdx)
                    try:
                        WebDriverWait(driver, 1, 0.5).\
                            until(lambda x:prdWaiting.is_displayed() is True)
                    except TimeoutException:
                        pass
                    try:
                        WebDriverWait(driver, 5, 0.5).\
                            until(lambda x:prdWaiting.is_displayed() is False)
                    except TimeoutException as ex:
                        pass
                    numResults=waitText(numResultsCss,3,0.5)
                    if numResults is None:
                        continue
                    numResults=int(re.search(r"\d+", numResults).group(0))
                    print('numResults=',numResults)
                    if numResults >10:
                        waitClickable("#lnkAllDownloadMore",3).click()
                    try:
                        erItems=getElems('a.register-product.navlistsearch',3, 0.5)
                    except TimeoutException:
                        erItems=getElems('div#LargeFirmware > ul > li > div > p > a.navlistsearch',3)

                    if len(erItems) != numResults:
                        print('Error, numResults=%d, but len(erItems)=%d'
                              %(numResults, len(erItems)))
                    for itemIdx, erItem in enumerate(erItems):
                        if not erItem.is_displayed():
                            print('itemIdx=%d is not displayed()' % itemIdx)
                            continue
                        desc = getElemText(erItem)
                        uprint('desc="%s"'%desc)
                        if 'firmware' not in desc.lower():
                            continue
                        fw_url = erItem.get_attribute('data-durl')
                        if not fw_url:
                            fw_url = erItem.get_attribute('fw_url')
                        print('fw_url=', fw_url)
                        if not fw_url:
                            continue
                        if not fw_url.startswith('http'):
                            print('Error: fw_url=', fw_url)
                            continue
                        executor.submit(download_file, prdTxt, desc, fw_url)
                        # download_file(prdTxt, desc, fw_url)
        catIdx, famIdx, prdIdx = None, None, None
        return catIdx, famIdx, prdIdx
    except BaseException as ex:
        traceback.print_exc()
        dumpSnapshot('netgear_crawler.py.png')
    finally:
        driver.quit()
        return catIdx, famIdx, prdIdx


def main():
    try:
        executor = ThreadPoolExecutor()
        os.makedirs(dlDir, exist_ok=True)
        with open('netgear_filelist.csv', 'w') as fout:
            cw = csv.writer(fout)
            cw.writerow(['model', 'fw_ver', 'fileName', 'fw_url', 'fw_date', 'fileSize', 'sha1', 'md5'])
        catIdx = int(sys.argv[1]) if len(sys.argv)>1 else 0
        famIdx = int(sys.argv[2]) if len(sys.argv)>2 else 0
        prdIdx = int(sys.argv[3]) if len(sys.argv)>3 else 0
        while True:
            catIdx, famIdx, prdIdx = main1(catIdx, famIdx, prdIdx, executor)
            if catIdx is None:
                return
            assert famIdx is not None
            assert prdIdx is not None
            print("\n[main] Continue from cat,fam,prd=(%d,%d,%d)\n" %
                  (catIdx, famIdx, prdIdx))
    except BaseException as ex:
        traceback.print_exc()
    finally:
        executor.shutdown(True)



if __name__=='__main__':
    try:
        main()
    except BaseException as ex:
        traceback.print_exc()

