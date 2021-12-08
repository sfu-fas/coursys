from ..db2_query import DB2_Query
import datetime

import string

class EmailQuery(DB2_Query):
    title = "Email Query"
    description = "Fetch a complete list of student-to-email mappings" 
    query = string.Template("""
    SELECT 
        EMPLID,
        E_ADDR_TYPE,
        EMAIL_ADDR,
        PREF_EMAIL_FLAG
    FROM 
        PS_EMAIL_ADDRESSES
        """)
    default_arguments = {}
    # keep this data for 2 weeks
    expires = datetime.datetime.now() + datetime.timedelta(14) 

    @staticmethod
    def preferred_email(row_map):
        return row_map['PREF_EMAIL_FLAG'] == 'Y'
    
    @staticmethod
    def campus_email(row_map):
        return row_map['E_ADDR_TYPE'] == 'CAMP'
        

class NameQuery(DB2_Query):
    title = "Name Query"
    description = "Fetch a complete list of student-to-full-name mappings" 
    query = string.Template("""
    SELECT DISTINCT 
        EMPLID,
        NAME_DISPLAY 
    FROM 
        PS_PERSONAL_DATA
        """)
    default_arguments = {}
    # keep this data for 2 weeks
    expires = datetime.datetime.now() + datetime.timedelta(14) 
    
class SexQuery(DB2_Query):
    title = "Sex Query"
    description = "Fetch a complete list of student-to-sex mappings" 
    query = string.Template("""
    SELECT DISTINCT 
        EMPLID,
        SEX
    FROM 
        PS_PERSONAL_DATA
        """)
    default_arguments = {}
    # keep this data for 2 weeks
    expires = datetime.datetime.now() + datetime.timedelta(14) 

class PreferredPhoneQuery(DB2_Query):
    title = "Phone Query"
    description = "Fetch a complete list of student-to-phone mappings"
    query = string.Template("""
    SELECT DISTINCT
        EMPLID,
        PHONE_TYPE,
        COUNTRY_CODE,
        PHONE,
        EXTENSION
    FROM
        PS_PERSONAL_PHONE
    WHERE 
        PREF_PHONE_FLAG = 'Y'""")

    default_arguments = {}
    # keep this data for 2 weeks
    expires = datetime.datetime.now() + datetime.timedelta(14) 

    @staticmethod
    def combined_number(row_map):
        ext = ""
        country = ""
        if row_map["EXTENSION"] != '':
            ext = " Ext#: " + row_map["EXTENSION"]
        if row_map["COUNTRY_CODE"] != '':
            country = "(" + row_map["COUNTRY_CODE"] + ") "
        return country + row_map['PHONE'] + ext

class OriginQuery(DB2_Query):
    title = "Origin Query"
    description = "Fetch a complete list of student-to-high-school/college/transfer-uni mappings"
    query = string.Template("""
    SELECT DISTINCT 
        A.EMPLID,
        A.EXT_CAREER,
        B.DESCR AS ORIGIN_NAME
    FROM 
        PS_EXT_COURSE A
    INNER JOIN PS_EXT_ORG_TBL B ON
        A.EXT_ORG_ID = B.EXT_ORG_ID""")
    default_arguments = {}
    # keep this data for 2 weeks
    expires = datetime.datetime.now() + datetime.timedelta(14) 
    @staticmethod
    def high_school(row_map):
        return row_map['EXT_CAREER'] == 'HS'


class NationalityQuery(DB2_Query):
    title = "Nationality Query"
    description = "Fetch a complete list of student-to-nationality mappings." 
    query = string.Template("""
    SELECT DISTINCT
        A.EMPLID,
        A.COUNTRY_OTHER, 
        B.DESCR
    FROM 
        PS_PERSONAL_DATA A
    INNER JOIN PS_COUNTRY_TBL B ON
        A.COUNTRY_OTHER = B.COUNTRY
    """)
    default_arguments = {}
    expires = datetime.datetime.now() + datetime.timedelta(14) 


