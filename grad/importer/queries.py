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
        SELECT 'CommitteeMembership', SC.EMPLID, SC.COMMITTEE_ID, AP.ACAD_PROG, COM.EFFDT, COM.COMMITTEE_TYPE, MEM.EMPLID, MEM.COMMITTEE_ROLE
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
        ORDER BY COM.EFFDT""",
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