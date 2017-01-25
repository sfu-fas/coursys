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
        SELECT 'ProgramStatusChange', emplid, stdnt_car_nbr, adm_appl_nbr, acad_prog, prog_status, prog_action, prog_reason,
            effdt, effseq, admit_term, exp_grad_term, degr_chkout_stat
        FROM ps_acad_prog
        WHERE acad_career='GRAD' AND acad_prog=%s AND effdt>=%s AND admit_term>=%s
        ORDER BY effdt, effseq
    """, (acad_prog, IMPORT_START_DATE, IMPORT_START_SEMESTER))
    return list(db)

@SIMS_problem_handler
@cache_by_args
def grad_appl_program_changes(acad_prog):
    """
    ps_adm_appl_data records where the fee has actually been paid: we don't bother looking at them until then.
    Rows become ApplProgramChange objects.

    Many of these will duplicate ps_acad_prog: the ProgramStatusChange is smart enough to identify them.
    """
    db = SIMSConn()
    db.execute("""
        SELECT 'ApplProgramChange', prog.emplid, prog.stdnt_car_nbr, prog.adm_appl_nbr, prog.acad_prog, prog.prog_status, prog.prog_action, prog.prog_reason,
            prog.effdt, prog.effseq, prog.admit_term, prog.exp_grad_term
        FROM ps_adm_appl_prog prog
            LEFT JOIN dbcsown.ps_adm_appl_data data
                ON prog.emplid=data.emplid AND prog.acad_career=data.acad_career AND prog.stdnt_car_nbr=data.stdnt_car_nbr AND prog.adm_appl_nbr=data.adm_appl_nbr
        WHERE prog.acad_career='GRAD' AND prog.acad_prog=%s AND prog.effdt>=%s AND prog.admit_term>=%s
            AND ( data.appl_fee_status in ('REC', 'WVD')
                OR data.adm_appl_ctr in ('GRAW') )
        ORDER BY prog.effdt, prog.effseq
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
        SELECT 'GradSemester', emplid, strm, stdnt_car_nbr, withdraw_code, acad_prog_primary, unt_taken_prgrss
        FROM ps_stdnt_car_term
        WHERE acad_career='GRAD' AND emplid in %s AND strm>=%s
            AND unt_taken_prgrss>0
        ORDER BY strm
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
        SELECT 'CommitteeMembership', st.emplid, st.committee_id, st.acad_prog, com.effdt, com.committee_type, mem.emplid, mem.committee_role
        FROM
            ps_stdnt_advr_hist st
            JOIN ps_committee com
                ON (com.institution=st.institution AND com.committee_id=st.committee_id AND st.effdt<=com.effdt)
            JOIN ps_committee_membr mem
                ON (mem.institution=st.institution AND mem.committee_id=st.committee_id AND com.effdt=mem.effdt)
        WHERE
            st.emplid in %s
            AND com.committee_type IN ('GSSUPER', 'GSEXAMING')
        ORDER BY com.effdt""",
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
        SELECT atbl.accomplishment, atbl.descr
        FROM ps_accomp_tbl atbl
        WHERE atbl.accomp_category='LNG'""", ())
    langs = dict(db)

    db.execute("""
        SELECT country, descr FROM ps_country_tbl""", ())
    countries = dict(db)

    db.execute("""
        SELECT visa_permit_type, visa_permit_class, descrshort FROM ps_visa_permit_tbl WHERE eff_status='A'""", ())
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
        SELECT acad_org, sfu_ga_res_area, descr50
        FROM ps_sfu_ga_resareas areas
        WHERE areas.eff_status='A'
            AND areas.effdt = (SELECT max(effdt) FROM ps_sfu_ga_resareas tmp
                WHERE areas.acad_org=tmp.acad_org AND areas.sfu_ga_res_area=tmp.sfu_ga_res_area)""", ())
    areas = dict(((acad_org, area), descr) for acad_org, area, descr in db)


    db.execute("""
        SELECT acad_org, sfu_ga_res_area, sfu_ga_reschoices, descr50
        FROM ps_sfu_ga_reschoic choices
        WHERE choices.effdt = (SELECT max(effdt) FROM ps_sfu_ga_reschoic tmp
            WHERE choices.acad_org=tmp.acad_org AND choices.sfu_ga_res_area=tmp.sfu_ga_res_area
            AND choices.sfu_ga_reschoices=tmp.sfu_ga_reschoices)""", ())
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
        SELECT 'GradMetadata', p.emplid, e.email_addr, a.accomplishment, cit.country, v.visa_permit_type, v.effdt,
            case when (a.accomplishment='ENG') then 0 else 1 end s1,
            case when (cit.country='CAN') then 0 else 1 end s2
        FROM ps_personal_data p
        LEFT JOIN ps_email_addresses e
            ON (p.emplid=e.emplid AND e.pref_email_flag='Y' and e.e_addr_type<>'INAC')
        LEFT JOIN ps_accomplishments a
            ON (a.emplid=p.emplid AND a.native_language='Y')
        LEFT JOIN ps_citizenship cit
            ON (cit.emplid=p.emplid)
        LEFT JOIN ps_visa_pmt_data v
            ON (p.emplid=v.emplid
                AND v.effdt = (SELECT MAX(tmp.effdt)
                    FROM ps_visa_pmt_data tmp
                    WHERE tmp.emplid = v.emplid
                    AND tmp.effdt <= current date ))
        WHERE p.emplid IN %s
        ORDER BY s1, s2, e.email_addr, a.accomplishment, cit.country, v.visa_permit_type""", (emplids,))
    return list(db)


@SIMS_problem_handler
@cache_by_args
def research_areas(emplids):
    """
    Research areas from these students' applications.
    """
    db = SIMSConn()
    db.execute("""
        SELECT 'GradResearchArea', emplid, adm_appl_nbr, acad_org, sfu_ga_res_area, sfu_ga_reschoices
        FROM ps_sfu_ga_res_det data
        WHERE data.emplid in %s""", (emplids,))
    return list(db)