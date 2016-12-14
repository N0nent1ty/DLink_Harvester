import requests
from form_submit import form_submit
import traceback
from lxml import html


startCat=0
startFam=0
startProd=0
startFirmware=0
def main():
    try:
        session = requests.Session()
        url='http://downloadcenter.netgear.com'
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
    except BaseException as ex:
        traceback.print_exc()


if __name__=='__main__':
    main()
