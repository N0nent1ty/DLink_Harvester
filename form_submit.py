import requests
from lxml import html
from lxml import etree
from urllib.parse import urljoin


def _select_value(ele, n, v):
    multiple = ele.multiple
    if v is None and not multiple:
        # Match browser behaviour on simple select tag without options selected
        # And for select tags wihout options
        o = ele.value_options
        return (n, o[0]) if o else (None, None)
    elif v is not None and multiple:
        # This is a workround to bug in lxml fixed 2.3.1
        # fix https://github.com/lxml/lxml/commit/57f49eed82068a20da3db8f1b18ae00c1bab8b12#L1L1139
        selected_options = ele.xpath('.//option[@selected]')
        v = [(o.get('value') or o.text or u'').strip() for o in selected_options]
    return n, v


def _value(ele):
    if ele.tag == 'select':
        return _select_value(ele, ele.name, ele.value)
    return ele.name, ele.value


def _get_inputs(form, formdata):
    formdata = dict(formdata or ())

    inputs = form.xpath('descendant::textarea'
                        '|descendant::select'
                        '|descendant::input[not(@type) or @type['
                        ' not(re:test(., "^(?:submit|image|reset)$", "i"))'
                        ' and (../@checked or'
                        '  not(re:test(., "^(?:checkbox|radio)$", "i")))]]',
                        namespaces={
                            "re": "http://exslt.org/regular-expressions"})
    values = [_value(e) for e in inputs]
    values = [(k,v if v is not None else '') for k,v in values if k and k not in formdata]

    values.extend(formdata.items())
    return values


def form_submit(session, response, formname, formdata, headers):
    root = html.fromstring(response.text)
    form = root.xpath('//form[@name="%s"]' % formname)[0]
    url = urljoin(response.url, form.action)
    formdata = _get_inputs(form, formdata)
    formdata = dict(formdata)
    return session.post(url=url, headers=headers, data=formdata)

def strip_js(url):
    return url.split('\'')[1]

iCategory=6-1
iFamily=16-1
iProduct=40-1
iFirmware=7-1
def main():
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

    root = html.fromstring(response.text)
    categories = root.xpath(".//select[@name='ctl00$ctl00$ctl00$mainContent$localizedContent$bodyCenter$adsPanel$lbProductCategory']/option")
    category = categories[iCategory]
    rsrc = category.xpath("./@value")[0]
    text = category.xpath(".//text()")[0]
    formdata= {"__EVENTTARGET": "ctl00$ctl00$ctl00$mainContent$localizedContent$bodyCenter$adsPanel$lbProductCategory",
               "ctl00$ctl00$ctl00$mainContent$localizedContent$bodyCenter$adsPanel$lbProductCategory": rsrc,
               "__ASYNCPOST:": "true"}
    response = form_submit(session, response,
                           "aspnetForm",
                           formdata,
                           {"Referer": response.url}
                           )

    root = html.fromstring(response.text)
    families = root.xpath("//select[@name='ctl00$ctl00$ctl00$mainContent$localizedContent$bodyCenter$adsPanel$lbProductFamily']/option")
    family = families[iFamily]
    rsrc = family.xpath("./@value")[0]
    text = family.xpath(".//text()")[0]
    formdata={"__EVENTTARGET": "ctl00$ctl00$ctl00$mainContent$localizedContent$bodyCenter$adsPanel$lbProductFamily",
              "ctl00$ctl00$ctl00$mainContent$localizedContent$bodyCenter$adsPanel$lbProductFamily": rsrc,
              "__ASYNCPOST:": "true"}
    response = form_submit(session, response,
                           "aspnetForm",
                           formdata,
                           {"Referer": response.url}
                           )
    root = html.fromstring(response.text)
    products = root.xpath("//select[@name='ctl00$ctl00$ctl00$mainContent$localizedContent$bodyCenter$adsPanel$lbProduct']/option")
    product = products[iProduct]
    rsrc = product.xpath("./@value")[0]
    text = product.xpath(".//text()")[0]
    formdata={"__EVENTTARGET": "ctl00$ctl00$ctl00$mainContent$localizedContent$bodyCenter$adsPanel$lbProduct",
              "ctl00$ctl00$ctl00$mainContent$localizedContent$bodyCenter$adsPanel$lbProduct": rsrc,
              "__ASYNCPOST:": "true"}
    response = form_submit(session, response,
                           "aspnetForm",
                           formdata,
                           {"Referer": response.url}
                           )

    root = html.fromstring(response.text)
    firmwares = root.xpath("//div[@id='LargeFirmware']//a")
    firmware = firmwares[iFirmware]
    href = firmware.xpath("./@data-durl")
    text = firmware.xpath(".//text()")
    if not href:
        href = firmware.xpath("./@href")
    if "firmware" in " ".join(text).lower():
        description = text[0]
        url = href[0]
        model = product.xpath(".//text()")[0]
        print(model, url, description)




if __name__=='__main__':
    main()


