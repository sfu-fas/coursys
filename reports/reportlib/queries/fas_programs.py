from ..db2_query import DB2_Query
import string

class AcadProgsOwnedByUnit(DB2_Query):
    title = "ACAD_PROGs owned by an ACAD_ORG"
    description = "Finds all ACAD_PROG that are owned (at least partially) by a unit"
    query = string.Template("""
        SELECT DISTINCT acad_prog
        FROM ps_acad_prog_tbl
        WHERE eff_status='A' AND acad_plan IN
            (SELECT DISTINCT acad_plan FROM ps_acad_plan_owner WHERE acad_org=$acad_org)
        """)

    default_arguments = {
        'acad_org': 'COMP SCI',
        }


class DegreeAcadProgs(DB2_Query):
    title = "ACAD_PROGs that are grant particular degrees"
    description = "Finds all ACAD_PROG that are grant a degree: probably BASc for Engineering programs"
    query = string.Template("""
        SELECT DISTINCT acad_prog
        FROM ps_acad_prog_tbl
        WHERE eff_status='A' AND acad_plan IN
            (SELECT DISTINCT acad_plan FROM ps_acad_plan_tbl WHERE degree in $degrees)
        """)

    default_arguments = {
        'degrees': ['BASC', 'BASC2', 'PAPSC'],
        }


def get_fas_programs():
    cmpt_progs = AcadProgsOwnedByUnit().result().column_as_list('ACAD_PROG')
    eng_progs = DegreeAcadProgs().result().column_as_list('ACAD_PROG')
    return (cmpt_progs, eng_progs)