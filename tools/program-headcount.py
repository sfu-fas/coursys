import sys, os
os.environ['DJANGO_SETTINGS_MODULE'] = 'courses.settings'
sys.path.append('.')
from coredata.queries import SIMSConn
import pprint
import csv, datetime, functools, json, itertools, collections


def program_headcount(strm):
    db = SIMSConn()
    query = """WITH STDNT_CAR_TERM AS
(   SELECT emplid
    FROM CS.PS_STDNT_CAR_TERM
    WHERE withdraw_code='NWD' AND strm=%s
), ACAD_PROG AS
(   SELECT emplid, stdnt_car_nbr
    FROM CS.PS_ACAD_PROG A
    WHERE prog_status='AC'
       AND effdt=(SELECT MAX(effdt) FROM CS.PS_ACAD_PROG WHERE emplid=A.emplid)
       AND effseq=(SELECT MAX(effseq) FROM CS.PS_ACAD_PROG WHERE emplid=A.emplid AND effdt=A.effdt)
), ACAD_PLAN AS
(   SELECT emplid, stdnt_car_nbr, acad_plan
    FROM CS.PS_ACAD_PLAN A
    WHERE effdt=(SELECT MAX(effdt) FROM CS.PS_ACAD_PLAN WHERE emplid=A.emplid)
       AND effseq=(SELECT MAX(effseq) FROM CS.PS_ACAD_PLAN WHERE emplid=A.emplid AND effdt=A.effdt)
), ACAD_PLAN_TBL AS
(   SELECT acad_plan, acad_plan_type, study_field, trnscr_descr descr
    FROM CS.PS_ACAD_PLAN_TBL A
    WHERE effdt=(SELECT MAX(effdt) FROM CS.PS_ACAD_PLAN_TBL WHERE acad_plan=A.acad_plan)
)
SELECT APL.acad_plan, APLT.descr, count(SCT.emplid) as headcount
FROM STDNT_CAR_TERM SCT INNER JOIN ACAD_PROG APR ON SCT.emplid=APR.emplid
    INNER JOIN ACAD_PLAN APL ON APR.emplid=APL.emplid AND APR.stdnt_car_nbr=APL.stdnt_car_nbr
    INNER JOIN ACAD_PLAN_TBL APLT ON APL.acad_plan=APLT.acad_plan
    INNER JOIN CS.PS_PERSONAL_DATA P ON SCT.emplid=P.emplid
    LEFT JOIN CS.PS_EMAIL_ADDRESSES E ON SCT.emplid=E.emplid
WHERE (APLT.study_field IN ('CMPT', 'ENSC', 'MSE') or APLT.acad_plan LIKE 'MSE%%')
    AND E.pref_email_flag = 'Y'
GROUP BY APL.acad_plan, APLT.descr
"""
    db.execute(query, (strm,))
    return list(db)



def main():
    strm = '1127'
    counts = program_headcount(strm)
    with open(strm+'.csv', 'wb') as csvfile:
        writer = csv.writer(csvfile)
        for row in counts:
            writer.writerow(row)


    
main()
