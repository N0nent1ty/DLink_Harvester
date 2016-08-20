#!/usr/bin/env python3
# -*- coding: utf8 -*-

import ftputil
import re
import sys
from os import path
import os
import zipfile
from infix_operator import Infix


def pjoin_fun(dir, fname):
    return path.join(dir, fname)
pjoin = Infix(pjoin_fun)

localstor='./output/D-Link/'
os.makedirs(localstor, exist_ok=True)
with ftputil.open('ftp.dlink.eu', 'anonymous', 'guest@about.com') as host:
    for roots, dirs, fnames in host.walkdir():
        for fname in fnames:
            if path.splitext(fname)[-1] != '.zip':
                continue
            host.download_file(root/pjoin/fname, localstor/pjoin/fname)
