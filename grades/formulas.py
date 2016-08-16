# based on http://pyparsing.wikispaces.com/file/view/simpleArith.py
# and http://pyparsing.wikispaces.com/file/view/simpleSQL.py

# Usual usage of the parser:
#   from grades.formulas import ...
# for each calculated grade:
#   parsed_expr = parse(formula)
# find all NumericActivities for the course and process into format for evaluator:
#   activities = NumericActivity.objects.filter(offering=c)
#   act_dict = activities_dictionary(activities)        
# then pass it into the evaluator along with a Member object for the student:
#   result = eval_parse(parsed_expr, act_dict, member, visible)

from pyparsing import ParseException
import itertools
from grades.models import NumericActivity

class EvalException(Exception):
    pass

def create_parser():
    """
    Build and return a parser for expressions.
    
    Parser builds a tuple-based representation of the formula the should be easy to evaluate.
    Each component is a tuple with:
       the first element indicats the type,
       the second element gives a set of columns referenced
       the rest gives the required arguments for the formula-chunk.
    
    Parser throws ParseException if something goes wrong.
    """
    from pyparsing import Literal, Word, Optional, CaselessLiteral, Group, StringStart, StringEnd, Suppress, CharsNotIn, Forward, nums, delimitedList, operatorPrecedence, opAssoc

    def column_parse(toks):
        """
        Parse a column name and strip off any ".foo" modifier.
        """
        col = toks[0][0]
        if col.endswith(".max"):
            col = col[:-4]
            return ("col", set([col]), col, 'max')
        elif col.endswith(".percent"):
            col = col[:-8]
            return ("col", set([col]), col, 'per')
        elif col.endswith(".final"):
            col = col[:-6]
            return ("col", set([col]), col, 'fin')
        else:
            return ("col", set([col]), col, 'val')

    def actionflag_parse(toks):
        """
        Parse the [[activitytotal]] special case
        """
        flag = toks[0][0]
        if flag == 'activitytotal':
            # dependant activity True is a flag meaning "everything": fixed later.
            return ("flag", set([True]), flag)
    
        raise ParseException, "Unknown flag ([[...]])."

    def real_parse(toks):
        return ("num", set(), float(''.join(toks)))

    def func_parse(toks):
        cols = set()
        cols.update(*(t[1] for t in toks[0][1:]))
        return ("func", cols) + tuple(toks[0])

    def expr_parse(s, loc, toks):
        ts = toks[0]
        if len(ts) == 2:
            # unary operator
            return ("sign", ts[1][1], ts[0]) + tuple(ts[1:])
        elif len(ts) > 1 and len(ts)%2==1:
            # one or more ops at the same level
            # build list of referenced columns:
            cols = set()
            cols.update(*(t[1] for t in ts[0::2]))
            return ("expr", cols, ts[0]) + tuple(ts[1:])
        else:
            raise ParseException, "Unknown expression parsed."

    sign = Literal("+") | Literal("-")
    real = (Word( nums ) + "." + Optional( Word(nums) ) +  # whole/decimal part
            Optional( CaselessLiteral("E") + Optional(sign) + Word(nums) ) # scientific notation part
            )
    integer = Word(nums)
    number = (real | integer).setParseAction(real_parse) # all numbers treated as floats to avoid integer arithmetic rounding

    # Allow anything except ']' in column names.  Let the limitations on sane column names be enforced somewhere else.
    actionflag = Group(Suppress('[[') + CharsNotIn('[]') + Suppress(']]') ).setParseAction(actionflag_parse)
    column = Group(Suppress('[') + CharsNotIn('[]') + Suppress(']') ).setParseAction(column_parse)
    expr = Forward()
    function_name = ( CaselessLiteral("SUM") | CaselessLiteral("AVG") | CaselessLiteral("MAX")
            | CaselessLiteral("MIN") | CaselessLiteral("BEST") )
    function = Group(function_name + Suppress('(') + delimitedList(expr) + Suppress(')')).setParseAction(func_parse)
    operand = number | column | function | actionflag

    signop = Literal("+") | Literal("-")
    multop = Literal("*") | Literal("/")
    plusop = Literal("+") | Literal("-")

    expr << operatorPrecedence( operand,
	[(signop, 1, opAssoc.RIGHT, expr_parse),
	 (multop, 2, opAssoc.LEFT, expr_parse),
	 (plusop, 2, opAssoc.LEFT, expr_parse),]
	)

    formula = StringStart() + expr + StringEnd()
    return formula

parser = create_parser()

def fix_used_acts(parsed, course, activity):
    """
    Fix the list of used activities: True is a flag for "all other activities that contribute to final percent"
    """
    acts = parsed[1]
    if True in acts:
        acts.remove(True)
        all_na = NumericActivity.objects.filter(offering=course, percent__gt=0).exclude(deleted=True)
        if activity is None:
            acts.update([a.short_name for a in all_na])
        else:
            acts.update([a.short_name for a in all_na if a.id != activity.id])

def parse(expr, course, activity):
    """
    Parse expression and return parse tree.
    """
    parsed = parser.parseString(expr)[0]
    fix_used_acts(parsed, course, activity)
    return parsed

def cols_used(tree):
    """
    Return the set of column/activity labels used in the parse tree
    """
    return tree[1]

def activities_dictionary(activities):
    """
    Process the collection of activities into a dictionary for faster lookup later.
    """
    return dict( itertools.chain(
            ((a.name,a) for a in activities),
            ((a.short_name,a) for a in activities)
            ))


def visible_grade(act, member, visible, calculating_leak=False):
    """
    Return student-visible grade on this activity

    "calculating_leak": use unreleased values, even if the activity is released. May leak those values to students, but
    it's what the instructor requested.
    """
    if not calculating_leak and visible and act.status != 'RLS':
        return 0.0
    grades = act.numericgrade_set.filter(member=member)
    if len(grades)==0:
        return 0.0
    grade = grades[0]
    if grade.flag == 'NOGR':
        return 0.0
    else:
        return float(grade.value)
    

def eval_parse(tree, activity, act_dict, member, visible):
    """
    Evaluate an expression given its parse tree and dictionary of column values.
    "visible" indicates whether the activity in question is visible to students or not.

    Throws EvalException if there's a problem with the expression tree.
    
    Throws KeyError for unknown column.
    """
    calculating_leak = activity.calculation_leak()
    t = tree[0]
    if t == 'sign' and tree[2] == '+':
        return eval_parse(tree[3], activity, act_dict, member, visible)
    elif t == 'sign' and tree[2] == '-':
        return -eval_parse(tree[3], activity, act_dict, member, visible)
    elif t == 'col':
        act = act_dict[tree[2]]
        part = tree[3]
        if part=="val":
            return visible_grade(act, member, visible, calculating_leak=calculating_leak)
        elif part=="max":
            return float(act.max_grade)
        elif part=="per":
            if act.percent:
                return float(act.percent)
            else:
                return 0.0
        elif part=="fin":
            if act.percent:
                grade = visible_grade(act, member, visible, calculating_leak=calculating_leak)
                max_grade = float(act.max_grade)
                if max_grade:
                    return grade/max_grade * float(act.percent)
                else:
                    return 0.0
            else:
                return 0.0

    elif t == 'num':
        return tree[2]
    elif t == 'expr':
        expr = list(tree)
        expr.reverse()
        expr.pop() # remove the 'expr' marker
        expr.pop() # remove the column set
        # extract first term
        val = eval_parse(expr.pop(), activity, act_dict, member, visible)
        while expr:
            # extract operator/operand pairs until they're all gone
            operator = expr.pop()
            operand = eval_parse(expr.pop(), activity, act_dict, member, visible)
            if operator == "+":
                val += operand
            elif operator == "-":
                val -= operand
            elif operator == "*":
                val *= operand
            elif operator == "/":
                if operand==0:
                    val = 0.0
                else:
                    val /= operand
            else:
                raise EvalException, "Unknown operator in parse tree: %s"%(operator,)
        return val
    elif t == 'func':
        func = tree[2]
        if func == 'SUM':
            return sum(eval_parse(t, activity, act_dict, member, visible) for t in tree[3:])
        elif func == 'MAX':
            return max(eval_parse(t, activity, act_dict, member, visible) for t in tree[3:])
        elif func == 'MIN':
            return min(eval_parse(t, activity, act_dict, member, visible) for t in tree[3:])
        elif func == 'AVG':
            if len(tree) == 3:
                return 0
            return sum(eval_parse(t, activity, act_dict, member, visible) for t in tree[3:]) / (len(tree)-3)
        elif func == 'BEST':
            # round first argument to an int: it's the number of best items to pick
            n = int(round( eval_parse(tree[3], activity, act_dict, member, visible) ) + 0.1)
            if n < 1:
                raise EvalException, 'Bad number of "best" selected, %i.'%(n,)
            if n > len(tree)-4:
                raise EvalException, "Not enough arguments to choose %i best."%(n,)
            marks = [eval_parse(t, activity, act_dict, member, visible) for t in tree[4:]]
            marks.sort()
            return sum(marks[-n:])
        else:
            raise EvalException, "Unknown function in parse tree: %s"%(func,)
    elif t == 'flag':
        flag = tree[2]
        if flag == 'activitytotal':
            # total [activity.final] for all activities
            total = 0.0
            fix_used_acts(tree, activity.offering, activity)
            for label in tree[1]:
                act = act_dict[label]
                grade = visible_grade(act, member, visible, calculating_leak=calculating_leak)
                max_grade = float(act.max_grade)
                if max_grade:
                    total += grade/max_grade * float(act.percent)
            return total
        else:
            raise EvalException, "Unknown flag in parse tree: %s" % (flag,)
    else:
        raise EvalException, "Unknown element in parse tree: %s" % (tree,)
    

def create_display(tree, act_dict):
    if isinstance(tree, basestring):
        return unicode(tree)
        
    t = tree[0]
    if t == 'sign' and tree[2] == '+':
        return create_display(tree[3])
    elif t == 'sign' and tree[2] == '-':
        return '-' + create_display(tree[3])
    elif t == 'col':
        act = act_dict[tree[2]]
        part = tree[3]
        if part=="val":
            return '[' + act.name + ']'
        elif part=="max":
            return unicode(act.max_grade)
        elif part=="per":
            if act.percent:
                return unicode(act.percent)
            else:
                return "0.0"
        elif part=="fin":
            if act.percent:
                return "[%s]/%s*%s" % (act.name, act.max_grade, act.percent)
            else:
                return "0"
    
    elif t == 'num':
        return unicode(tree[2])
    elif t == 'expr':
        return '('  + ' '.join((create_display(e, act_dict) for e in tree[2:])) + ')'
    elif t == 'func':
        if tree[2] == 'BEST':
            return 'BESTOF'
        else:
            return tree[2] + '(' + ', '.join((create_display(e, act_dict) for e in tree[3:])) + ')'
    elif t == 'flag':
        flag = tree[2]
        if flag == 'activitytotal':
            return "ATOTAL"
        else:
            raise EvalException, "Unknown flag in parse tree: %s" % (flag,)
    else:
        raise EvalException, "Unknown element in parse tree: %s"%(tree,)


def display_formula(activity, activities):
    """
    Return user-understandable version of this activity's formula
    """
    tree = parse(activity.formula, activity.offering, activity)
    act_dict = activities_dictionary(activities)
    return unicode(create_display(tree, act_dict))


