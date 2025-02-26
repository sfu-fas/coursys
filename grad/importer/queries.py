from coredata.queries import SIMSConn, SIMS_problem_handler, cache_by_args
from .parameters import IMPORT_START_DATE, IMPORT_START_SEMESTER

@SIMS_problem_handler
@cache_by_args
def grad_program_changes(acad_prog):
    """
    Records from ps_acad_prog about students' progress in this program. Rows become ProgramStatusChange objects.
    """
    db = SIMSConn()
    db.execute("""
        SELECT 'ProgramStatusChange', PROG.EMPLID, PROG.STDNT_CAR_NBR, ADM_APPL_NBR, PROG.ACAD_PROG, PROG.PROG_STATUS, 
        PROG.PROG_ACTION, PROG.PROG_REASON, PROG.EFFDT, PROG.EFFSEQ, PROG.ADMIT_TERM, PROG.EXP_GRAD_TERM, 
        PROG.DEGR_CHKOUT_STAT, APLAN.ACAD_SUB_PLAN
        FROM PS_ACAD_PROG PROG
            LEFT JOIN PS_ACAD_SUBPLAN APLAN ON PROG.EMPLID=APLAN.EMPLID AND PROG.EFFDT=APLAN.EFFDT
        WHERE PROG.ACAD_CAREER='GRAD' AND PROG.ACAD_PROG=%s AND PROG.EFFDT>=%s AND PROG.ADMIT_TERM>=%s
        ORDER BY EFFDT, EFFSEQ
    """, (acad_prog, IMPORT_START_DATE, IMPORT_START_SEMESTER))
    return list(db)

@SIMS_problem_handler
@cache_by_args
def grad_appl_program_changes(acad_prog):
    """
    ps_adm_appl_data records where the fee has actually been paid: we don't bother looking at them until then.
    Rows become ApplProgramChange objects.

    Many of these will duplicate ps_acad_prog: the ProgramStatusChange is smart enough to identify them.

    The 13th null argument has been added because ApplProgramChange subclasses ProgramStatusChange, which now requires
    an extra degr_chkout_stat argument to find the grad application/approved statuses.
    """
    db = SIMSConn()
    db.execute("""
        SELECT 'ApplProgramChange', PROG.EMPLID, PROG.STDNT_CAR_NBR, PROG.ADM_APPL_NBR, PROG.ACAD_PROG, PROG.PROG_STATUS, PROG.PROG_ACTION, PROG.PROG_REASON,
            PROG.EFFDT, PROG.EFFSEQ, PROG.ADMIT_TERM, PROG.EXP_GRAD_TERM, NULL, APLAN.ACAD_SUB_PLAN
        FROM PS_ADM_APPL_PROG PROG
          LEFT JOIN PS_ACAD_SUBPLAN APLAN ON PROG.EMPLID=APLAN.EMPLID AND PROG.EFFDT=APLAN.EFFDT
            LEFT JOIN PS_ADM_APPL_DATA DATA
                ON PROG.EMPLID=DATA.EMPLID AND PROG.ACAD_CAREER=DATA.ACAD_CAREER AND PROG.STDNT_CAR_NBR=DATA.STDNT_CAR_NBR AND PROG.ADM_APPL_NBR=DATA.ADM_APPL_NBR
        WHERE PROG.ACAD_CAREER='GRAD' AND PROG.ACAD_PROG=%s AND PROG.EFFDT>=%s AND PROG.ADMIT_TERM>=%s
            AND ( DATA.APPL_FEE_STATUS IN ('REC', 'WVD')
                OR DATA.ADM_APPL_CTR IN ('GRAW') )
        ORDER BY PROG.EFFDT, PROG.EFFSEQ
    """, (acad_prog, IMPORT_START_DATE, IMPORT_START_SEMESTER))
    return list(db)

@SIMS_problem_handler
@cache_by_args
def grad_semesters(emplids):
    """
    Semesters when the student was taking classes: use to mark them active (since sometimes ps_acad_prog doesn't).
    """
    db = SIMSConn()
    db.execute("""
        SELECT 'GradSemester', EMPLID, STRM, STDNT_CAR_NBR, WITHDRAW_CODE, ACAD_PROG_PRIMARY, UNT_TAKEN_PRGRSS
        FROM PS_STDNT_CAR_TERM
        WHERE ACAD_CAREER='GRAD' AND EMPLID IN %s AND STRM>=%s
            AND UNT_TAKEN_PRGRSS>0
        ORDER BY STRM
    """, (emplids, IMPORT_START_SEMESTER))
    return list(db)

@SIMS_problem_handler
@cache_by_args
def committee_members(emplids):
    """
    Grad committee members for this person.

    I suspect the JOIN is too broad: possibly should be maximizing effdt in ps_stdnt_advr_hist?
    """
    db = SIMSConn()
    db.execute("""
        WITH CM AS (
            SELECT SC.EMPLID AS S_EMPLID, SC.COMMITTEE_ID, AP.ACAD_PROG, COM.EFFDT, COM.COMMITTEE_TYPE, MEM.EMPLID, MEM.COMMITTEE_ROLE,
            ROW_NUMBER() OVER (PARTITION BY MEM.EMPLID, AP.ACAD_PROG,
            CASE
                WHEN MEM.COMMITTEE_ROLE='MMBR' THEN 'SUPR'
                WHEN MEM.COMMITTEE_ROLE='STDN' THEN 'SUPR'
                WHEN MEM.COMMITTEE_ROLE='FADV' THEN 'SNRS'
                ELSE MEM.COMMITTEE_ROLE
            END
            ORDER BY COM.EFFDT DESC) AS RN,
            MAX(COM.EFFDT) OVER (PARTITION BY AP.ACAD_PROG, SC.EMPLID) AS 'MAX_EFFDT'
            FROM
                PS_SFU_STDNT_CMTTE SC
                JOIN (SELECT * FROM (
                        SELECT EMPLID, ACAD_CAREER, STDNT_CAR_NBR, ACAD_PROG,
                                RANK () OVER (PARTITION BY EMPLID, ACAD_CAREER, STDNT_CAR_NBR ORDER BY EFFDT DESC) AS DATE_RANK 
                        FROM PS_ACAD_PROG
                        ) DR WHERE DR.DATE_RANK = 1
                    ) AP
                    ON SC.EMPLID = AP.EMPLID AND SC.ACAD_CAREER = AP.ACAD_CAREER AND SC.STDNT_CAR_NBR = AP.STDNT_CAR_NBR
                JOIN PS_COMMITTEE COM
                    ON (COM.INSTITUTION = SC.INSTITUTION AND COM.COMMITTEE_ID = SC.COMMITTEE_ID AND SC.EFFDT <= COM.EFFDT)
                JOIN PS_COMMITTEE_MEMBR MEM
                    ON (MEM.INSTITUTION = SC.INSTITUTION AND MEM.COMMITTEE_ID = SC.COMMITTEE_ID AND COM.EFFDT = MEM.EFFDT)
            WHERE
                SC.EMPLID IN %s
                AND COM.COMMITTEE_TYPE IN ('GSSUPER', 'GSEXAMING')
        )
        SELECT 'CommitteeMembership', CM.S_EMPLID AS EMPLID, CM.COMMITTEE_ID, CM.ACAD_PROG, CM.EFFDT, CM.COMMITTEE_TYPE, CM.EMPLID, CM.COMMITTEE_ROLE, CM.MAX_EFFDT
        FROM CM
        WHERE RN = 1
        ORDER BY EFFDT""",
        (emplids,))
    return list(db)

@SIMS_problem_handler
@cache_by_args
def grad_scholarships(emplids):
    """ 
    Grad scholarships for this person
    """
    db = SIMSConn()
    db.execute("""
        WITH strm_Data AS 
            (SELECT *, RANK () OVER (PARTITION BY BUSINESS_UNIT ORDER BY STRM DESC) AS date_Rank 
                FROM PS_TERM_DEFLT_TBL
                WHERE EFF_STATUS = 'A')
        
        SELECT 'ScholarshipDisbursement', EMPLID, AID_YEAR, ITEM_TYPE, ACAD_CAREER, DISBURSEMENT_ID, STRM, DESCR, DISBURSED_BALANCE, ACAD_PROG, 
                CASE
                    WHEN ITEM_TYPE = 433000000225 AND STRM < 1247 THEN 0
                    WHEN ITEM_TYPE = 433000000226 AND STRM < 1247 THEN 0
                    WHEN ITEM_TYPE = 433000000227 AND STRM < 1247 THEN 0
                    WHEN ITEM_TYPE = 433100000007 THEN 0
                    WHEN ITEM_TYPE = 433100000008 THEN 0
                    WHEN ITEM_TYPE = 433100000004 THEN 0
                    WHEN ITEM_TYPE = 433100000005 THEN 0
                    WHEN ITEM_TYPE = 433100000006 THEN 0
                    WHEN ITEM_TYPE = 403000000241 THEN 0
                    WHEN ITEM_TYPE = 403000000242 THEN 0
                    WHEN ITEM_TYPE = 403000000143 THEN 0
                    WHEN ITEM_TYPE = 423000000061 THEN 0
                    WHEN ITEM_TYPE = 423000000062 THEN 0
                    WHEN ITEM_TYPE = 423000000063 THEN 0
                    WHEN ITEM_TYPE = 403000000460 THEN 0
                    WHEN ITEM_TYPE = 443000000001 THEN 0
                    WHEN ITEM_TYPE = 443000000002 THEN 0
                    WHEN ITEM_TYPE = 443000000003 THEN 0
                    ELSE 1
                END AS ELIGIBLE
            FROM (
                SELECT SA.EMPLID, SA.AID_YEAR, SA.ITEM_TYPE, SA.ACAD_CAREER, SA.DISBURSEMENT_ID, FIN_AID_TYPE, SA.STRM, IT.DESCR, SA.DISBURSED_BALANCE, org_Status.ACAD_PROG,
                    RANK () OVER (PARTITION BY SA.EMPLID, SA.AID_YEAR, SA.ITEM_TYPE, SA.ACAD_CAREER, SA.DISBURSEMENT_ID, SA.STRM, IT.DESCR, SA.DISBURSED_BALANCE ORDER BY org_Status.STDNT_CAR_NBR DESC) AS DUPLICATES
                    FROM PS_STDNT_AWRD_DISB SA
                    INNER JOIN (
                        SELECT * 
                            FROM (
                                SELECT ITEM_TYPE, EFF_STATUS, AID_YEAR, DESCR, FIN_AID_TYPE, RANK () OVER (PARTITION BY ITEM_TYPE, AID_YEAR ORDER BY EFFDT DESC) AS DATE_RANK 
                                    FROM PS_ITEM_TYPE_FA
                                    WHERE EFF_STATUS IN ('A') AND ITEM_TYPE NOT IN (433000000012, 433000000013, 433000000014, 433000000183, 433000000184, 433000000185) AND FIN_AID_TYPE IN ('GA', 'GE', 'GF', 'GS')
                            ) DR WHERE DR.DATE_RANK = 1
                        ) IT
                        ON SA.ITEM_TYPE = IT.ITEM_TYPE AND SA.AID_YEAR = IT.AID_YEAR
                    JOIN (
                        SELECT DATA1.EMPLID, DATA1.ACAD_CAREER, DATA1.STDNT_CAR_NBR, DATA1.ACAD_PROG, DATA1.ADMIT_TERM, DATA1.COMPLETION_TERM, SD.STRM AS LATEST_TERM, DATA1.translated_Status AS END_STAT 
                            FROM (	
                                SELECT *, RANK () OVER (PARTITION BY EMPLID, ACAD_CAREER, STDNT_CAR_NBR ORDER BY EFFDT DESC, EFFSEQ DESC) AS date_Rank
                                    FROM (
                                        SELECT *, 
                                            CASE
                                                WHEN PROG_STATUS = 'AC' AND PROG_ACTION = 'MATR' THEN 'CONF'
                                                WHEN PROG_STATUS = 'CN' AND PROG_ACTION = 'WADM' THEN 'CANC'
                                                WHEN PROG_STATUS = 'AC' AND PROG_ACTION = 'ACTV' THEN 'ACTI'
                                                WHEN PROG_STATUS = 'DC' AND PROG_ACTION = 'DISC' THEN 'WIDR'
                                                WHEN PROG_STATUS = 'DE' AND PROG_ACTION = 'DISC' THEN 'WIDR'
                                                WHEN PROG_STATUS = 'LA' AND PROG_ACTION = 'LEAV' THEN 'LEAV'
                                                WHEN PROG_STATUS = 'AC' AND PROG_ACTION = 'RLOA' THEN 'ACTI'
                                                WHEN PROG_STATUS = 'AC' AND PROG_ACTION = 'RADM' THEN 'ACTI'
                                                WHEN PROG_STATUS = 'CM' AND PROG_ACTION = 'COMP' THEN 'GRAD'
                                                ELSE 'None'
                                            END AS translated_Status
                                            FROM PS_ACAD_PROG
                                        ) DATA1
                                    WHERE DATA1.translated_Status NOT IN ('None')
                                    ) DATA1
                            JOIN (
                                SELECT sd1.STRM, sd1.TERM_END_DT AS TERM_END, sd2.TERM_END_DT AS PREV_TERM_END
                                    FROM strm_Data sd1
                                    JOIN strm_Data sd2 ON sd1.date_Rank = sd2.date_Rank - 1) SD
                                ON DATA1.EFFDT >= SD.PREV_TERM_END AND DATA1.EFFDT < SD.TERM_END
                                WHERE DATA1.date_Rank = 1) org_Status
                        ON SA.EMPLID = org_Status.EMPLID AND SA.ACAD_CAREER = org_Status.ACAD_CAREER AND SA.STRM >= org_Status.ADMIT_TERM AND org_Status.END_STAT IN ('ACTI', 'CONF', 'LEAV')
                            OR SA.EMPLID = org_Status.EMPLID AND SA.ACAD_CAREER = org_Status.ACAD_CAREER AND SA.STRM >= org_Status.ADMIT_TERM AND SA.STRM <= org_Status.LATEST_TERM AND org_Status.END_STAT IN ('WIDR', 'CANC') AND org_Status.ADMIT_TERM <> org_Status.LATEST_TERM
                            OR SA.EMPLID = org_Status.EMPLID AND SA.ACAD_CAREER = org_Status.ACAD_CAREER AND SA.STRM >= org_Status.ADMIT_TERM AND SA.STRM <= org_Status.COMPLETION_TERM AND org_Status.END_STAT IN ('GRAD')
                    WHERE SA.DISBURSED_BALANCE > 0) final
                WHERE final.DUPLICATES = 1 AND final.EMPLID IN %s
                ORDER BY EMPLID DESC, STRM DESC, DISBURSED_BALANCE DESC""",
        (emplids,))
    return list(db)

@SIMS_problem_handler
@cache_by_args
def metadata_translation_tables():
    """
    Translation tables of SIMS values to english. Fetched once into a dict to save joining many things later.
    """
    db = SIMSConn()
    db.execute("""
        SELECT ATBL.ACCOMPLISHMENT, ATBL.DESCR
        FROM PS_ACCOMP_TBL ATBL
        WHERE ATBL.ACCOMP_CATEGORY='LNG'""", ())
    langs = dict(db)

    db.execute("""
        SELECT COUNTRY, DESCR FROM PS_COUNTRY_TBL""", ())
    countries = dict(db)

    db.execute("""
        SELECT VISA_PERMIT_TYPE, VISA_PERMIT_CLASS, DESCRSHORT FROM PS_VISA_PERMIT_TBL WHERE EFF_STATUS='A'""", ())
    visas = dict((typ, (cls, desc)) for typ, cls, desc in db)

    return langs, countries, visas

@SIMS_problem_handler
@cache_by_args
def research_translation_tables():
    """
    Translation tables of SIMS values to english. Fetched once into a dict to save joining many things later.
    """
    db = SIMSConn()
    db.execute("""
        SELECT ACAD_ORG, SFU_GA_RES_AREA, DESCR50
        FROM PS_SFU_GA_RESAREAS AREAS
        WHERE AREAS.EFF_STATUS='A'
            AND AREAS.EFFDT = (SELECT MAX(EFFDT) FROM PS_SFU_GA_RESAREAS TMP
                WHERE AREAS.ACAD_ORG=TMP.ACAD_ORG AND AREAS.SFU_GA_RES_AREA=TMP.SFU_GA_RES_AREA)""", ())
    areas = dict(((acad_org, area), descr) for acad_org, area, descr in db)


    db.execute("""
        SELECT ACAD_ORG, SFU_GA_RES_AREA, SFU_GA_RESCHOICES, DESCR50
        FROM PS_SFU_GA_RESCHOIC CHOICES
        WHERE CHOICES.EFFDT = (SELECT MAX(EFFDT) FROM PS_SFU_GA_RESCHOIC TMP
            WHERE CHOICES.ACAD_ORG=TMP.ACAD_ORG AND CHOICES.SFU_GA_RES_AREA=TMP.SFU_GA_RES_AREA
            AND CHOICES.SFU_GA_RESCHOICES=TMP.SFU_GA_RESCHOICES)""", ())
    choices = dict(((acad_org, area, choice), descr) for acad_org, area, choice, descr in db)

    return areas, choices


@SIMS_problem_handler
@cache_by_args
def grad_metadata(emplids):
    """
    Metadata about a grad student: application email address, native language, citizenship, work visa status.

    LEFT JOINs many things onto ps_personal_data to get lots out of the way in one query.
    """
    db = SIMSConn()
    # The s1, s2 column are to sort so we get the "good" language/country first: let speaking English or being Canadian
    # win (since they might be better for that student's TA/RA appointments later).
    # Other sort orders just to make sure we get the same record tomorrow if there are other duplicates (visa can duplicate)
    db.execute("""
        SELECT 'GradMetadata', P.EMPLID, E.EMAIL_ADDR, A.ACCOMPLISHMENT, CIT.COUNTRY, V.VISA_PERMIT_TYPE, V.EFFDT,
            CASE WHEN (A.ACCOMPLISHMENT='ENG') THEN 0 ELSE 1 END S1,
            CASE WHEN (CIT.COUNTRY='CAN') THEN 0 ELSE 1 END S2
        FROM PS_PERSONAL_DATA P
        LEFT JOIN PS_EMAIL_ADDRESSES E
            ON (P.EMPLID=E.EMPLID AND E.PREF_EMAIL_FLAG='Y' and E.E_ADDR_TYPE<>'INAC')
        LEFT JOIN PS_ACCOMPLISHMENTS A
            ON (A.EMPLID=P.EMPLID AND A.NATIVE_LANGUAGE='Y')
        LEFT JOIN PS_CITIZENSHIP CIT
            ON (CIT.EMPLID=P.EMPLID)
        LEFT JOIN PS_VISA_PMT_DATA V
            ON (P.EMPLID=V.EMPLID
                AND V.EFFDT = (SELECT MAX(TMP.EFFDT)
                    FROM PS_VISA_PMT_DATA TMP
                    WHERE TMP.EMPLID = V.EMPLID
                    AND TMP.EFFDT <= GETDATE() ))
        WHERE P.EMPLID IN %s
        ORDER BY S1, S2, E.EMAIL_ADDR, A.ACCOMPLISHMENT, CIT.COUNTRY, V.VISA_PERMIT_TYPE""", (emplids,))
    return list(db)


@SIMS_problem_handler
@cache_by_args
def research_areas(emplids):
    """
    Research areas from these students' applications.
    """
    db = SIMSConn()
    db.execute("""
        SELECT 'GradResearchArea', EMPLID, ADM_APPL_NBR, ACAD_ORG, SFU_GA_RES_AREA, SFU_GA_RESCHOICES
        FROM PS_SFU_GA_RES_DET DATA
        WHERE DATA.EMPLID IN %s""", (emplids,))
    return list(db)