#!/usr/bin/env python3
# coding: utf-8
# import harvest_utils
# from harvest_utils import waitClickable, waitText, getElems, \
#    getElemText, waitTextChanged, waitElem, getText
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.common.exceptions import \
    TimeoutException
import sys
import csv
import re
import os
import requests
from dateutil.parser import parse as parse_date
import urllib
import traceback
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver # noqa
from web_utils import uprint, getFileSha1, getFileMd5
# import selenium
from selenium.webdriver import PhantomJS
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import WebDriverException

dlDir = './output/netgear/downloadcenter.netgear.com/'


class WebElemX(WebElement):
    def xpath(xp: str, timeout: float=5, pollFreq: float=0.5) -> WebElement:
        begin = time.time()
        while (time.time() - begin) < timeout:
            try:
                return super().find_element_by_xpath(xp)
            except:
                time.sleep(pollFreq)
        return None


def waitClickable(self, css: str, timeOut: float=60, pollFreq: float=3) -> WebElement: # noqa
    wait = WebDriverWait(self, timeOut, poll_frequency=pollFreq)
    return wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, css)))

PhantomJS.waitClickable = waitClickable


def waitVisible(self, css: str, timeOut: float=60, pollFreq: float=3.0) -> WebElement: # noqa
    wait = WebDriverWait(self, timeOut, poll_frequency=pollFreq)
    return wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR,css)))

PhantomJS.waitVisible = waitVisible


def waitText(self, css: str,timeOut: float=60, pollFreq: float=3.0) -> str:
    begin = time.time()
    while (time.time()-begin) < timeOut:
        try:
            return self.waitVisible(css, pollFreq).text
        except (TimeoutException, StaleElementReferenceException):
            time.sleep(pollFreq)
            timeElapsed += (time.time()-beginTime)
            continue
        except Exception as ex:
            print(ex)
            return None
    return None

PhantomJS.waitText = waitText


def getText(self:PhantomJS, css:str,timeout:float=60,pollFreq:float=3)->str:
    begin = time.time()
    while (time.time() - begin ) < timeout:
        try:
            # return self.execute_script("return document.querySelector('%s').textContent"%css)
            return self.find_element_by_css_selector(css).text
        except:
            time.sleep(pollFreq)
    return None

PhantomJS.getText = getText


def waitTextChanged(self:PhantomJS, css:str, oldText:str, timeout=60, pollFreq=0.5) -> str:
    begin = time.time()
    while (time.time() - begin) < timeout:
        newText = self.getText(css)
        if newText != oldText:
            return newText
        else:
            time.sleep(pollFreq)
    raise TimeoutException('[waitTextChanged] text unchanged: "%s"'%(oldText))

PhantomJS.waitTextChanged = waitTextChanged

def waitElem(self: PhantomJS, css: str,timeOut: float=60) -> WebElement:
    wait = WebDriverWait(self, timeOut, poll_frequency=3.0)
    return wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,css)))

PhantomJS.waitElem = waitElem


def getElems(self, css:str,timeOut:float=60, pollFreq:float=3.0) -> [WebElement]:
    self.waitVisible(css, timeOut, pollFreq)
    return self.find_elements_by_css_selector(css)

PhantomJS.getElems = getElems


def getElemText(self: WebElement, timeOut: float=60.0, pollFreq=3.0) -> str:
    while (time.time()-begin) < timeOut:
        try:
            return self.text.strip()
        except StaleElementReferenceException:
            time.sleep(pollFreq)
    raise TimeoutException("[getElemText] elem=%s"%WebElement)

WebElement.getElemTet = getElemText


def download_file(model, fileName, fw_url):
    try:
        resp = requests.get(url=fw_url, stream=True)
        if 'Content-Length' in resp.headers:
            fileSize = int(resp.headers['Content-Length'])
            print('fileSize=', fileSize)
        else:
            fileSize = None
        fw_ver = re.search(r'\d+(\.\d+)+', fileName).group(0)
        fileName = os.path.basename(urllib.parse.urlsplit(fw_url).path)
        print('fileName=', fileName)
        if 'Last-Modified' in resp.headers:
            fw_date = resp.headers['Last-Modified']
            fw_date = parse_date(fw_date)
        else:
            fw_date = None
        if os.path.isfile(dlDir + fileName) \
                and fileSize == os.path.getsize(dlDir + fileName):
            print('already downloaded: ', fileName)
        else:
            print('start downloading: ', fw_url)
            with open(dlDir + fileName + '.downloading', 'wb') as fout:
                for chunk in resp.iter_content(8192):
                    fout.write(chunk)
            os.rename(dlDir + fileName + '.downloading', dlDir + fileName)
            print('finished downloading: ', fw_url)
        sha1 = getFileSha1(dlDir + fileName)
        md5 = getFileMd5(dlDir + fileName)
        fileSize = os.path.getsize(dlDir + fileName)
        with open('netgear_filelist.csv', 'a') as fout:
            cw = csv.writer(fout)
            cw.writerow([model, fw_ver, fileName, fw_url,
                         fw_date, fileSize, sha1, md5])
    except BaseException as ex:
        traceback.print_exc()
        print(ex)


def main():
    os.makedirs(dlDir, exist_ok=True)
    startCatIdx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    startFamIdx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    startPrdIdx = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    executor = ThreadPoolExecutor()
    PhantomJS.waitClickable = waitClickable
    driver = PhantomJS()
    # harvest_utils.driver = driver
    with open('netgear_filelist.csv', 'w') as fout:
        cw = csv.writer(fout)
        cw.writerow(['model', 'fw_ver', 'fileName', 'fw_url',
                     'fw_date', 'fileSize', 'sha1', 'md5'])
    driver.get('http://downloadcenter.netgear.com/')
    # click DrillDown
    driver.waitClickable('#ctl00_ctl00_ctl00_mainContent_localizedContent_bodyCenter_BasicSearchPanel_btnAdvancedSearch').click() # noqa
    ctl00 = "#ctl00_ctl00_ctl00_mainContent_localizedContent_bodyCenter_adsPanel_" # noqa ignore=E501
    #
    # wait Page2
    try:
        catSel = Select(driver.waitClickable(ctl00 + "lbProductCategory"))
        numCat = len(catSel.options)
        for catIdx in range(startCatIdx, numCat):
            catSel = Select(driver.waitClickable(ctl00 + "lbProductCategory"))
            print('catIdx=', catIdx)
            catTxt = catSel.options[catIdx].text
            uprint('catTxt= ' + catTxt)
            oldText = driver.getText(ctl00 + "lbProductFamily")
            catSel.select_by_index(catIdx)
            driver.waitTextChanged(ctl00 + "lbProductFamily", oldText)
            famSel = Select(driver.waitClickable(ctl00 + "lbProductFamily"))
            numFam = len(famSel.options)
            for famIdx in range(startFamIdx, numFam):
                famSel = Select(driver.waitClickable(ctl00 + "lbProductFamily")) # noqa
                print('famIdx=', famIdx)
                startFamIdx = 0
                famTxt = famSel.options[famIdx].text
                uprint('famTxt= ' + famTxt)
                oldText = driver.getText(ctl00 + "lbProduct")
                famSel.select_by_index(famIdx)
                driver.waitTextChanged(ctl00 + "lbProduct", oldText)
                prdSel = Select(driver.waitClickable(ctl00 + "lbProduct"))
                numPrd = len(prdSel.options)
                for prdIdx in range(startPrdIdx, numPrd):
                    prdSel = Select(driver.waitClickable(ctl00 + "lbProduct"))
                    startPrdIdx = 0
                    print("catIdx,famIdx,prdIdx=%d, %d, %d" %
                          (catIdx, famIdx, prdIdx))
                    prdTxt = prdSel.options[prdIdx].text
                    uprint('cat,fam,prd="%s","%s","%s"' % (catTxt, famTxt, prdTxt)) # noqa ignore=E501
                    prdWaiting = driver.waitElem(ctl00 + "upProgProductLoader > div > img") # noqa ignore=E501
                    prdSel.select_by_index(prdIdx)
                    try:
                        WebDriverWait(driver, 1, 0.5).\
                            until(lambda x: prdWaiting.is_displayed() is True)
                    except TimeoutException:
                        pass
                    try:
                        WebDriverWait(driver, 5, 0.5).\
                            until(lambda x: prdWaiting.is_displayed() is False)
                    except TimeoutException as ex:
                        pass
                    numResults = driver.waitText(ctl00 + "lvwAllDownload_lblAllDownloadResult", 3, 0.5) # noqa ignore=E501
                    if numResults is None:
                        continue
                    numResults = int(re.search(r"\d+", numResults).group(0))
                    print('numResults=', numResults)
                    if numResults > 10:
                        driver.waitClickable("#lnkAllDownloadMore", 3).click()
                    try:
                        erItems = driver.getElems('a.register-product.navlistsearch', 3, 0.5) # noqa
                    except TimeoutException:
                        erItems = driver.getElems('div#LargeFirmware > ul > li > div > p > a.navlistsearch', 3) # noqa ignore=E501

                    if len(erItems) != numResults:
                        print('Error, numResults=%d, but len(erItems)=%d'
                              % (numResults, len(erItems)))
                    for itemIdx, erItem in enumerate(erItems):
                        if not erItem.is_displayed():
                            print('itemIdx=%d is not displayed()' % itemIdx)
                            continue
                        erItem.getItemText = getItemText
                        desc = erItem.getElemText(erItem)
                        uprint('desc="%s"' % desc)
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
    except BaseException as ex:
        traceback.print_exc()
        import pdb; pdb.set_trace()
        driver.save_screenshot("netgear_crawler2")
    finally:
        driver.quit()
        executor.shutdown(True)


if __name__ == '__main__':
    try:
        main()
    except BaseException as ex:
        print(ex)
