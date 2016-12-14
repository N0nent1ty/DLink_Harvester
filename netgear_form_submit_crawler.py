import requests
from form_submit import form_submit
import traceback
from lxml import html


iCategory=6-1
iFamily=16-1
iProduct=40-1
iFirmware=7-1
def main():
    try:
        session = requests.Session()
        response = session.get(url='http://downloadcenter.netgear.com')
        root = html.fromstring(response.text)
        href = root.xpath(".//a[@id='ctl00_ctl00_ctl00_mainContent_localizedContent_bodyCenter_BasicSearchPanel_btnAdvancedSearch']/@href")
        href = strip_js(href[0])
        formdata = {"__EVENTTARGET": href}
        response = form_submit(session, response,
                               "aspnetForm",
                               formdata,
                               {"Referer": response.url}
                               )
        walkCategories(session, response)
    except BaseException as ex:
        traceback.print_exc()


def strip_js(url):
    return url.split('\'')[1]


def walkCategories(session, response):
    try:
        root = html.fromstring(response.text)
        categories = root.xpath(".//select[@name='ctl00$ctl00$ctl00$mainContent$localizedContent$bodyCenter$adsPanel$lbProductCategory']/option")
        for iCat, category in enumerate(categories):
            rsrc = category.xpath("./@value")[0]
            text = category.xpath(".//text()")[0]
            # print('Category="%s", iCat=%d'%(text, iCat))
            formdata= {"__EVENTTARGET": "ctl00$ctl00$ctl00$mainContent$localizedContent$bodyCenter$adsPanel$lbProductCategory",
                       "ctl00$ctl00$ctl00$mainContent$localizedContent$bodyCenter$adsPanel$lbProductCategory": rsrc,
                       "__ASYNCPOST:": "true"}
            response = form_submit(session, response,
                                   "aspnetForm",
                                   formdata,
                                   {"Referer": response.url}
                                   )
            walkFamilies(session, response)
    except BaseException as ex:
        traceback.print_exc()


def walkFamilies(session, response):
    try:
        root = html.fromstring(response.text)
        families = root.xpath("//select[@name='ctl00$ctl00$ctl00$mainContent$localizedContent$bodyCenter$adsPanel$lbProductFamily']/option")
        for iFam, family in enumerate(families):
            rsrc = family.xpath("./@value")[0]
            text = family.xpath(".//text()")[0]
            # print('Family="%s", iFam=%d'%(text, iFam))
            formdata={"__EVENTTARGET": "ctl00$ctl00$ctl00$mainContent$localizedContent$bodyCenter$adsPanel$lbProductFamily",
                      "ctl00$ctl00$ctl00$mainContent$localizedContent$bodyCenter$adsPanel$lbProductFamily": rsrc,
                      "__ASYNCPOST:": "true"}
            response = form_submit(session, response,
                                   "aspnetForm",
                                   formdata,
                                   {"Referer": response.url}
                                   )
            walkProducts(response, session)
    except BaseException as ex:
        traceback.print_exc()


def walkProducts(response, session):
    try:
        root = html.fromstring(response.text)
        products = root.xpath("//select[@name='ctl00$ctl00$ctl00$mainContent$localizedContent$bodyCenter$adsPanel$lbProduct']/option")
        for iProd, product in enumerate(products):
            rsrc = product.xpath("./@value")[0]
            text = product.xpath(".//text()")[0]
            # print('Product="%s", iProd=%d'%(text, iProd))
            formdata={"__EVENTTARGET": "ctl00$ctl00$ctl00$mainContent$localizedContent$bodyCenter$adsPanel$lbProduct",
                      "ctl00$ctl00$ctl00$mainContent$localizedContent$bodyCenter$adsPanel$lbProduct": rsrc,
                      "__ASYNCPOST:": "true"}
            response = form_submit(session, response,
                                   "aspnetForm",
                                   formdata,
                                   {"Referer": response.url}
                                   )
            walkFirmwares(response, product)
    except BaseException as ex:
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
    except BaseException as ex:
        traceback.print_exc()


if __name__=='__main__':
    main()
