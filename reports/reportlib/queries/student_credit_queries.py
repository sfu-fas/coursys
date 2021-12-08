from ..db2_query import DB2_Query
import string


class StudentsTotalCreditsQueryWithSTRM(DB2_Query):
    title = "Total Credits For a Single Student"
    description = "Find the maximum amount of total credits for the given students, and the matching semester."

    query = string.Template("""
    SELECT DISTINCT
      T.EMPLID,
      T.TOT_CUMULATIVE AS CREDITS,
      T.STRM
      FROM PS_STDNT_CAR_TERM T
      INNER JOIN
      (SELECT EMPLID,
        MAX(TOT_CUMULATIVE) AS MAX_CREDITS
        FROM  PS_STDNT_CAR_TERM
        WHERE EMPLID IN $emplids
        GROUP BY EMPLID) Q
      on T.EMPLID = Q.EMPLID AND T.TOT_CUMULATIVE = Q.MAX_CREDITS
    """)
    default_arguments = {'emplids': ['301008183']}


class StudentsTotalCreditsQuery(DB2_Query):
    title = "Total Credits For a Single Student"
    description = "Find the maximum amount of total credits for the given students."

    query = string.Template("""
    SELECT DISTINCT
      T.EMPLID,
      T.TOT_CUMULATIVE AS CREDITS
      FROM PS_STDNT_CAR_TERM T
      INNER JOIN
      (SELECT EMPLID,
        MAX(TOT_CUMULATIVE) AS MAX_CREDITS
        FROM  PS_STDNT_CAR_TERM
        WHERE EMPLID IN $emplids
        GROUP BY EMPLID) Q
      ON T.EMPLID = Q.EMPLID AND T.TOT_CUMULATIVE = Q.MAX_CREDITS
    """)
    default_arguments = {'emplids': ['301008183']}
