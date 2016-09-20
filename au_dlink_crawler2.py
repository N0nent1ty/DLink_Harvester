import re
from urllib import parse
from pyquery import PyQuery as pq
import csv


def csvinit():
    with open('au_dlink_filelist.csv','w') as fout:
        cw = csv.writer(fout)
        cw.writerow(['model','rev','fw_ver','fw_url'])
def csvwrite(model,rev,fw_ver,fw_url):
    with open('au_dlink_filelist.csv','a') as fout:
        cw = csv.writer(fout)
        cw.writerow([model,rev,fw_ver,fw_url])

model="DIR-600"
page_url = "http://support.dlink.com.au/Download/download.aspx?product=%s"%parse.quote(model)
d = pq(url=page_url)
csvinit()

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
            csvwrite(model,rev,fw_ver,fw_url)
            print('"%s" "%s" "%s"  %s'%(model,rev,fw_ver,fw_url))

# fin = open('au_dlink_BrainTree_DUB-1312.html')
# content = fin.read()
# fin.close()
# content = content.splitlines()
# for line in content:
#     line = line.strip()
#     if 'Downloads for' in line:
#         m = re.search(r'javascript:GetDocument\((\d+)\)',line,re.I)
#         docId = m.group(1)
#         pons = requests.get('http://faq.dlink.com.au/supportfaq/DisplayTemplate.aspx?TemplateId=%(docId)s'%locals(),
#                 headers={'Referer':"http://faq.dlink.com.au/supportfaq/BrainTree.aspx"})

