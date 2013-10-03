"""
    Rules.py is just a collection of data that represents
    business rules that are likely to change. 
"""

programs = {
        'CMPT':'Computing Science',
        'CMPT2':'Computing Science 2: Second Degree', # I wish this were a hollywood blockbuster
        'BGSAP':'BGSAP',
        'ENSC':'Engineering',
        'ENSC2':'Engineering: Second Degree',
        'ENBUX':'ENBUX'
    }

program_groups = {}
program_groups['cmpt_undergrad_programs'] = ['CMPT', 'CMPT2']
program_groups['bgs_undergrad_programs'] = ['BGSAP']
program_groups['ensc_undergrad_programs'] = ['ENSC', 'ENBUX', 'ENSC2']

program_groups['fas_undergrad_programs'] =  program_groups['cmpt_undergrad_programs'] + program_groups['bgs_undergrad_programs'] + program_groups['ensc_undergrad_programs']

program_groups['cmpt_grad_programs'] = ['CPPHD', 'CPPZU', 'CPMSC', 'CPMCW', 'CPMZU']
program_groups['ensc_grad_programs'] = ['ESPHD', 'ESMAS', 'ESMEN']

program_groups['fas_grad_programs'] = program_groups['cmpt_grad_programs'] + program_groups['ensc_grad_programs']

program_groups['ensc_all_programs'] = program_groups['ensc_undergrad_programs'] + program_groups['ensc_grad_programs']
program_groups['cmpt_all_programs'] = program_groups['cmpt_undergrad_programs'] + program_groups['cmpt_grad_programs']
program_groups['fas_all_programs'] = program_groups['fas_undergrad_programs'] + program_groups['fas_grad_programs']

plans = {
        'CMPTMAJ':"CMPT Major",
        'DCMPT':"CMPT Degree Program",
        'CMPTMIN':"CMPT Minor", 
        'CMPTHON':"CMPT Honours",
        'CMPTJMA':"CMPT Joint Major",
        'CMPTJHO':"CMPT Joint Honours",
        'SOSYMAJ':"Software Systems Major",
        'ZUSFU':"CMPT Zhejiang University",
        'MACMMAJ':"MACM Major",
        'MACMHON':"MACM Honours",
        'DBGSAP':"BGS Degree Placeholder",
        'GISMAJ':"Geography/Information Systems Major",
        'GISHON':"Geography/Information Systems Honours",
        'ENSCPRO':'Engineering Science Program',
        'MSEMAJ':"Mechatronics Major",
        'MSEHON':"Mechatronics Honours",
        'MSSCMAJ': "Management Systems Science Major",
        'MSSCHON': "Management Systems Science Honours",
        'COGSMAJ': "Cognitive Science Major",
        'COGSHON': "Cognitive Science Honours"
    }


plan_groups = {}
plan_groups['cmpt_plans'] = ['CMPTMAJ', 'CMPTHON', 'CMPTJMA', 'CMPTJHO', 'MACMMAJ', 'MACMHON', 
                                            'DCMPT', 'ZUSFU', 'CMPTMIN', 'SOSYMAJ', 'GISHON', 'GISMAJ']
plan_groups['bgs_plans'] = ['DBGSAP']
plan_groups['ensc_plans'] = ['ENSCPRO', 'MSEMAJ', 'MSEHON']
plan_groups['misc_plans'] = ['MSSCMAJ', 'MSSCHON', 'COGSMAJ', 'COGSHON']
plan_groups['fas_plans'] = plan_groups['cmpt_plans'] + plan_groups['bgs_plans'] + plan_groups['ensc_plans'] + plan_groups['misc_plans']

