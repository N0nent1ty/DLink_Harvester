from lxml import html
# from lxml import etree
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

