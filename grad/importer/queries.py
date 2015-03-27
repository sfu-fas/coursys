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
            effdt, effseq, admit_term, exp_grad_term
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
        ORDER BY com.effdt""",
        (emplids,))
    return list(db)