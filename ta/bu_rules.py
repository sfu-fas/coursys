from coredata.models import Semester
import math
import decimal

CMPT_BU_ALLOCATION_CONSTANT = 0.062
CMPT_BU_ALLOCATION_CONSTANT_1224 = 0.08

def semester_1134():
    return Semester.objects.get(name="1134")

def default_strategy( posting, offering, count=None ):
    return decimal.Decimal(0)

def cmpt_before_1134_strategy( posting, offering, count=None ):
    if count is None:
        count = offering.enrl_tot
    level = offering.number[0] + "00"
    if level not in posting.bu_defaults():
        return decimal.Decimal(0)
    
    defaults = posting.bu_defaults()[level]
    defaults.sort()
    # get highest cutoff <= actual student count
    last = decimal.Decimal(0)
    for s,b in defaults:
        if s > count:
            return decimal.Decimal(last)
        last = b
    return decimal.Decimal(last) # if off the top of scale, return max

def cmpt_after_1134_strategy( posting, offering, count=None ):
    if count is None:
        count = offering.enrl_tot
    default = math.floor( count * CMPT_BU_ALLOCATION_CONSTANT )
    if default < 2:
        return decimal.Decimal(0)
    return decimal.Decimal(str(default))

def cmpt_after_1224_strategy( posting, offering, count=None ):
    if count is None:
        count = offering.enrl_tot
    default = math.floor( count * CMPT_BU_ALLOCATION_CONSTANT_1224 )
    if default < 2:
        return decimal.Decimal(0)
    return decimal.Decimal(str(default))

def cmpt_after_1234_strategy( posting, offering, count=None ):
    if count is None:
        count = offering.enrl_tot
    default = round(count * CMPT_BU_ALLOCATION_CONSTANT_1224, 2)
    if default < 2:
        return decimal.Decimal(0)
    return decimal.Decimal(str(default))  

def does_bu_strategy_involve_defaults( semester, unit ):
    if unit.label in ["CMPT", "COMP"] and semester.name < '1134':
        return True
    return False

def get_bu_strategy( semester, unit ):
    if unit.label in ["CMPT", "COMP"] and semester.name < '1134':
        return cmpt_before_1134_strategy
    if unit.label in ["CMPT", "COMP"] and '1134' <= semester.name <= '1221':
        return cmpt_after_1134_strategy
    if unit.label in ["CMPT", "COMP"] and semester.name >= '1224' and semester.name <= '1231':
        return cmpt_after_1224_strategy
    if unit.label in ["CMPT", "COMP"] and semester.name >= '1234':
        return cmpt_after_1234_strategy
    return default_strategy
