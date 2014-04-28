from ..db2_query import DB2_Query
import datetime

import string

class EmailQuery(DB2_Query):
    title = "Email Query"
    description = "Fetch a complete list of student-to-email mappings" 
    query = string.Template("""
    SELECT 
        emplid,
        e_addr_type,
        email_addr,
        pref_email_flag
    FROM 
        ps_email_addresses
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
        emplid,
        name_display 
    FROM 
        ps_personal_data
        """)
    default_arguments = {}
    # keep this data for 2 weeks
    expires = datetime.datetime.now() + datetime.timedelta(14) 
    
class SexQuery(DB2_Query):
    title = "Sex Query"
    description = "Fetch a complete list of student-to-sex mappings" 
    query = string.Template("""
    SELECT DISTINCT 
        emplid,
        sex
    FROM 
        ps_personal_data
        """)
    default_arguments = {}
    # keep this data for 2 weeks
    expires = datetime.datetime.now() + datetime.timedelta(14) 

class PreferredPhoneQuery(DB2_Query):
    title = "Phone Query"
    description = "Fetch a complete list of student-to-phone mappings"
    query = string.Template("""
    SELECT DISTINCT
        emplid,
        phone_type,
        country_code,
        phone,
        extension
    FROM
        ps_personal_phone
    WHERE 
        pref_phone_flag = 'Y'""")

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
        a.emplid,
        a.ext_career,
        b.descr AS origin_name
    FROM 
        ps_ext_course a
    INNER JOIN ps_ext_org_tbl b ON
        a.ext_org_id = b.ext_org_id""")
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
        a.emplid,
        a.country_other, 
        b.descr
    FROM 
        ps_personal_data a
    INNER JOIN ps_country_tbl b ON
        a.country_other = b.country
    """)
    default_arguments = {}
    expires = datetime.datetime.now() + datetime.timedelta(14) 


