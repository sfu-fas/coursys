import sys, os, itertools
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.append('.')
from coredata.queries import SIMSConn
import pprint
import csv

max_effdt = "(SELECT ap.emplid as emplid, ap.stdnt_car_nbr as stdnt_car_nbr, max(ap.effdt) as effdt FROM ps_acad_plan ap WHERE ap.emplid=%s GROUP BY ap.emplid, ap.stdnt_car_nbr)"
acad_plan = 'ZUSFU'

def main():
    db = SIMSConn()
    out = csv.writer(open(acad_plan+".csv", 'wb'))
    out.writerow(['Emplid', 'Name', 'Attempted Cred', 'As Of', 'CGPA'])
    
    query = "SELECT ap.emplid " \
            "FROM ps_acad_plan ap " \
            "WHERE ap.acad_plan=%s " \
            "GROUP BY ap.emplid ORDER BY ap.emplid"
    db.execute(query, (acad_plan,))
    all_emplids = [row[0] for row in list(db)]
    #all_emplids = all_emplids[:30]
    count = 0
    
    for emplid in all_emplids:
        query = "SELECT ap.stdnt_car_nbr " \
                "FROM ps_acad_plan ap, " + max_effdt + " as maxeffdt " \
                "WHERE maxeffdt.emplid=ap.emplid " \
                " AND maxeffdt.stdnt_car_nbr=ap.stdnt_car_nbr" \
                " AND ap.effdt=maxeffdt.effdt AND ap.acad_plan=%s " \
                "GROUP BY ap.stdnt_car_nbr"
        db.execute(query, (emplid,acad_plan))
        
        #print emplid, list(db)
        
        for (car_nbr,) in list(db):
            query = "SELECT ct.cum_gpa, ct.strm, ct.tot_taken_gpa, pd.name " \
                    "FROM ps_stdnt_car_term ct, ps_personal_data pd " \
                    "WHERE ct.emplid=pd.emplid AND ct.emplid=%s " \
                    " AND stdnt_car_nbr=%s " \
                    " AND tot_taken_gpa>0 " \
                    "ORDER BY strm DESC FETCH FIRST 1 ROWS ONLY"
            db.execute(query, (emplid,car_nbr))
            row = db.fetchone()
            #print emplid, car_nbr, row
            if not row:
                continue
            gpa, strm, taken, name = row
            out.writerow([emplid, name, taken, strm, gpa])
            count += 1
    
    out.writerow(['Average', None, None, None, "=AVERAGE(E2:E%i)"%(count+1)])

main()
