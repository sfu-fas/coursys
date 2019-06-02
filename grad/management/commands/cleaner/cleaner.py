
"""
A utility designed to clean up CSV data. 
"""

from .table import Table

import argparse
import os
import datetime
import copy
import re

parser = argparse.ArgumentParser(description='Clean all of the datas.')

parser.add_argument( '--input', dest='input', default=False, 
    help='The csv to clean up.')

args = parser.parse_args()

if not os.path.exists( args.input ):
    print(args.input, " is not a valid file path. Please provide an --input x.csv argument to cleaner.py.") 
    exit()

table = Table.from_csv( args.input )
output_table = copy.deepcopy( table ) 

NEWLINE = "_x000B_"

# convert all "_x000B_" characters to newlines. 
#for row in table.rows:
#    for i in xrange(0, len(row)):
#        row[i] = row[i].replace(NEWLINE, "\n")

groups = { 
    'sin': [ "SIN", "SFU ID" ], 
    'semesters': [ "Semester of Approval of Supervisory Committee", 
                "Convocation Semester", 
                "Semester of Approval of Examining Committee", 
                "First Semester", 
                "Semester Left" ],
    'dates': ["Date of Birth", 
            "M.Eng. Progress", 
            "Ph.D. Progress", 
            "M.A.Sc. Progress"],
    'datetime_and_location': [ "PhD Qualifying Exam", "Thesis Date" ],
}

def sin_clean( sin_ugly ):
    
    no_spaces_or_dashes = sin_ugly.replace(" ", "").replace("-", "").replace("\n", "").replace(NEWLINE, "")
    
    if len(no_spaces_or_dashes) == 9: 
        return int(no_spaces_or_dashes)
    else:
        return ""

def date_clean( date_ugly ):

    if date_ugly == "":
        return ""
    
    formats = [ "%m/%d/%Y", "%d-%m-%Y", "%Y", "%b-%y", "%A, %B %d, %Y", "%y-%b", "%b. %Y" ] 

    for fmt in formats:
        try:
            python_datetime = datetime.datetime.strptime( date_ugly, fmt )
            break
        except ValueError: 
            python_datetime = False
            continue

    if python_datetime:
        if python_datetime.year < 1900:
            return "" 
        return python_datetime.strftime( "%d-%m-%y" )
    else:
        return "" 

def list_in_string( string, lst ):
    return sum([ string.find(x) for x in lst ]) != -(len(lst)) 

def semester_clean( semester_ugly ):
    semester_ugly = semester_ugly.lower().strip()

    # First, if ####?
    try:
        if len(semester_ugly) == 4 and int(semester_ugly) > 999 and int(semester_ugly) < 10000:
            return semester_ugly
    except ValueError:
        pass

    # Then, if ##-#?
    try:
        if len(semester_ugly) == 4 and semester_ugly.index("-") == 2:
            yr = semester_ugly[0:2] 
            term = semester_ugly[3:4]
            
            if term == "2":
                term = "4"
            if term == "3":
                term = "7"

            if yr[0] == "9":
                first_character = "0"
            else:
                first_character = "1"
            second_two_characters = yr
            last_character = str(term)

            return first_character + second_two_characters + last_character
    except ValueError:
        pass

    digits = re.findall(r'\d+', semester_ugly)
    if len(digits) > 0:
        digits = digits[0]
    else:
        return ""

    if len(digits) == 4:
        if digits[0] == "1":
            first_character = "0"
        else:
            first_character = "1"
        second_two_characters = digits[2:4]
    elif len(digits) == 2:
        if digits[0] == "9":
            first_character = "0"
        else:
            first_character = "1"
        second_two_characters = digits
    else:
        return ""
    
    # If not that, then try _Identifier_ _Year_
    springs = ["spring", "jan", "feb", "mar", "apr"]
    summers = ["summer", "sum", "may", "jun", "july", "aug"]
    falls = ["fall", "sep", "oct", "nov", "dec"] 
    if list_in_string( semester_ugly, springs ):
        last_character = "1"
    elif list_in_string( semester_ugly, summers ):
        last_character = "4"
    elif list_in_string( semester_ugly, falls ):
        last_character = "7"
    else:
        return ""

    return first_character + second_two_characters + last_character

for group_name, group in groups.items():
    
    # Create a table mapping data ("Dr. Mark Peters") to what we assume that data should look like ("3092929292")
    translation_table = {}
    
    for column in group:
        column = column.upper()
        for row in table.row_maps():
            clean_attempt = ""
            if group_name == 'sin':
                clean_attempt = sin_clean( row[column] )
            if group_name == 'dates':
                clean_attempt = date_clean( row[column] )
            if group_name == 'semesters':
                clean_attempt = semester_clean( row[column] )
            translation_table[ row[ column ] ] = clean_attempt
        if os.path.exists( group_name + ".csv" ):
            t = Table.from_csv( group_name + ".csv" ) 
            for row in t.rows:
                if row[0] in translation_table and translation_table[ row[0] ] != "" and row[1] == "":
                    pass
                else:
                    translation_table[ row[0] ] = row[1]
        column_index = table.headers.index(column)
        for row in output_table.rows:
            if row[column_index] in translation_table and translation_table[row[column_index]] != "":
                row[column_index] = translation_table[row[column_index]]

    t = Table()

    t.append_column( group_name )
    t.append_column( "canonical" )
    for key, value in translation_table.items():
        t.append_row( [ key, value ] )
    t.to_csv( group_name + ".csv")

output_table.to_csv( "output.csv" )
