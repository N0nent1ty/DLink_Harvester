from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from io import StringIO
from pdfminer.pdfinterp import process_pdf
import logging


def convert(fp):
    logger = logging.getLogger()
    logger.propagate = False
    logging.getLogger().setLevel(logging.ERROR)
    caching = True
    rsrcmgr = PDFResourceManager(caching=caching)
    pagenos=set()
    maxpages=0
    password=''
    with StringIO() as output:
        try:
            device = TextConverter(rsrcmgr, output, laparams=LAParams())
            process_pdf(rsrcmgr, device, fp, pagenos, maxpages=maxpages, password=password,
                        caching=caching, check_extractable=True)
            return output.getvalue()
        finally:
            device.close()


def convert_pdf_file(fname):
    with open(fname, 'rb') as fp:
        return convert(fp)


def main():
    import sys
    fname = sys.argv[1]
    txt = convert_pdf_file(fname)
    print(txt)
if __name__=='__main__':
    main()
