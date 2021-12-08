from ..db2_query import DB2_Query
import string

class AcadProgsOwnedByUnit(DB2_Query):
    title = "ACAD_PROGs owned by an ACAD_ORG"
    description = "Finds all ACAD_PROG that are owned (at least partially) by a unit"
    query = string.Template("""
        SELECT DISTINCT ACAD_PROG
        FROM PS_ACAD_PROG_TBL
        WHERE EFF_STATUS='A' AND ACAD_PLAN IN
            (SELECT DISTINCT ACAD_PLAN FROM PS_ACAD_PLAN_OWNER WHERE ACAD_ORG=$acad_org)
        """)

    default_arguments = {
        'acad_org': 'COMP SCI',
        }


class DegreeAcadProgs(DB2_Query):
    title = "ACAD_PROGs that grant particular degrees"
    description = "Finds all ACAD_PROG that grant a degree: probably BASc for Engineering programs"
    query = string.Template("""
        SELECT DISTINCT ACAD_PROG
        FROM PS_ACAD_PROG_TBL
        WHERE EFF_STATUS='A' AND ACAD_PLAN IN
            (SELECT DISTINCT ACAD_PLAN FROM PS_ACAD_PLAN_TBL WHERE DEGREE IN $degrees)
        """)

    default_arguments = {
        'degrees': ['BASC', 'BASC2', 'PAPSC'],
        }


def get_fas_programs():
    cmpt_progs = AcadProgsOwnedByUnit().result().column_as_list('ACAD_PROG')
    eng_progs = DegreeAcadProgs().result().column_as_list('ACAD_PROG')
    return (cmpt_progs, eng_progs)