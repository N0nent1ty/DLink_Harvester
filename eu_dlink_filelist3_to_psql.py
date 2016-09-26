import psycopg2
import csv
from datetime import datetime


idgreaterthan=814
idlessorequal=4968

try:
    db = psycopg2.connect(database='firmware',user='firmadyne',password='firmadyne',host='127.0.0.1')
    cur = db.cursor()
    cur.execute("SELECT id,filename,hash FROM image WHERE id>%(idgreaterthan)d AND id<=%(idlessorequal)d "
            "ORDER BY id"%locals())
    rows = cur.fetchall()
    with open('eu_dlink_filelist3.csv', 'r') as fin:
        cr = csv.reader(fin)
        next(cr)
        for model,fw_ver,fw_url,fsize,fdate,sha1,md5 in cr:
            fname = fw_url.split('/')[-1]
            fdate = datetime.strptime(fdate, "%Y-%m-%d %H:%M:%S")
            try:
                iid, fname2 = next((_[0],_[1]) for _ in rows if _[2]==md5)
            except StopIteration:
                print('%(md5)s is not found in psql'%locals())
                cur.execute("INSERT INTO image "
                        "(brand,filename,file_url,model,version,rel_date,file_size,file_sha1,hash) VALUES"
                        "('D-Link',%(fname)s,%(fw_url)s,%(model)s,%(fw_ver)s,%(fdate)s,%(fsize)s,%(sha1)s,%(md5)s)",
                        locals())
                db.commit()
                continue
            if fname2!=fname:
                print('%(fname)s and %(fname2)s have same md5 %(md5)s'%locals())
                fname = fname2
            cur.execute("UPDATE image SET filename=%(fname)s, file_url=%(fw_url)s, model=%(model)s,"
                    "version=%(fw_ver)s, rel_date=%(fdate)s, file_size=%(fsize)s, file_sha1=%(sha1)s,"
                    " brand='D-Link' WHERE id=%(iid)s", locals())
            db.commit()
            print('%d %s %s %s'%(iid, fname,model,fw_ver))
except Exception as ex:
    print(ex)
finally:
    db.close()

