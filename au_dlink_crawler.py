# -*- coding: utf8 -*-
import re

prefix=[]
suffix=[]
with open('au_dlink_model_select.html') as fin:
    for line in fin:
        line = line.strip()
        if line.startswith('<option value="">Select</option>'):
            while True:
                line = next(fin)
                m = re.search(r'value="(\w+)"', line.strip(), re.I)
                if not m:
                    break
                prefix += [m.group(1)]
            suffix = [None for i in range(len(prefix))]
        elif line.startswith('group[0][0]=new Option("","")'):
            while True:
                line = next(fin)
                m= re.search(r'group\[(\d+)\]\[(\d+)\]=new\s+Option\("(\w+)',line.strip(), re.I)
                if not m:
                    break
                if m.group(3).strip().lower().startswith('select'):
                    continue
                index = int(m.group(1))
                index-=1
                if suffix[index] is None:
                    suffix[index] = [m.group(3)]
                else:
                    suffix[index] += [m.group(3)]

for ipx, px in enumerate(prefix):
    for sx in suffix[ipx]:
        print('%s-%s'%(px,sx))


# prefix+=['ANT24']
# prefix+=['ANT70']
#
# suffix=[]
# suffix+= [['0401','0500','0501']]
# suffix+= [['0801','1000','1800']]
#

