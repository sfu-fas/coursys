from ..db2_query import DB2_Query
import string


class StudentsTotalCreditsQueryWithSTRM(DB2_Query):
    title = "Total Credits For a Single Student"
    description = "Find the maximum amount of total credits for the given students, and the matching semester."

    query = string.Template("""
    SELECT DISTINCT
      t.EMPLID,
      t.TOT_CUMULATIVE AS CREDITS,
      t.STRM
      FROM PS_STDNT_CAR_TERM t
      INNER JOIN
      (select EMPLID,
        MAX(TOT_CUMULATIVE) AS MAX_CREDITS
        from  ps_stdnt_car_term
        where EMPLID IN $emplids
        GROUP BY EMPLID) q
      on t.EMPLID = q.EMPLID AND t.TOT_CUMULATIVE = q.MAX_CREDITS
    """)
    default_arguments = {'emplids': ['301008183']}


class StudentsTotalCreditsQuery(DB2_Query):
    title = "Total Credits For a Single Student"
    description = "Find the maximum amount of total credits for the given students."

    query = string.Template("""
    SELECT DISTINCT
      t.EMPLID,
      t.TOT_CUMULATIVE AS CREDITS
      FROM PS_STDNT_CAR_TERM t
      INNER JOIN
      (select EMPLID,
        MAX(TOT_CUMULATIVE) AS MAX_CREDITS
        from  ps_stdnt_car_term
        where EMPLID IN $emplids
        GROUP BY EMPLID) q
      on t.EMPLID = q.EMPLID AND t.TOT_CUMULATIVE = q.MAX_CREDITS
    """)
    default_arguments = {'emplids': ['301008183']}
