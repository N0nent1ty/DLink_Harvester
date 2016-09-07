import csv
import psycopg2
from datetime import datetime


def main():
    try:
        db2 = psycopg2.connect(database='firmware',user='firmadyne',password='firmadyne',host='127.0.0.1')
        cur = db2.cursor()
        cur.execute('SELECT id,filename FROM image WHERE id>814 ORDER BY id')
        rows = cur.fetchall()
        with open('dlink_ftp.dlink.eu_filelist.csv', 'r') as fin:
            cr = csv.reader(fin,dialect='excel')
            next(cr)
            for ftpurl,fsize,fdate,model_ls,sha1,md5 in cr:
                fname = ftpurl.split('/')[-1]
                iid = next((_[0] for _ in rows if _[1]==fname),None)
                if not iid:
                    continue
                model_ls = eval(model_ls)
                fsize = int(fsize)
                fdate = datetime.strptime(fdate, '%Y-%m-%d %H:%M:%S')
                if not model_ls:
                    model=None
                else:
                    model=model_ls[0]
                print('%s  %s  %s %s'%(fname, iid, model, fdate))
                cur.execute('UPDATE image SET file_url=%(ftpurl)s, model=%(model)s, rel_date=%(fdate)s, '
                        'file_sha1=%(sha1)s WHERE id=%(iid)s', locals())
                db2.commit()
    finally:
        db2.close()


if __name__=='__main__':
    main()

