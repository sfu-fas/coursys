# based on http://pyparsing.wikispaces.com/file/view/simpleArith.py
# and http://pyparsing.wikispaces.com/file/view/simpleSQL.py

# Usual usage of the parser:
#   from grades.formulas import *
# for each calculated grade:
#   parsed_expr = parse(formula)
# find all NumericActivities for the course and process into format for evaluator:
#   activities = NumericActivity.objects.filter(offering=c)
#   act_dict = activities_dictionary(activities)        
# then pass it into the evaluator along with a Member object for the student:
#   result = eval_parse(parsed_expr, act_dict, member)

from external.pyparsing import ParseException
import itertools

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
    from external.pyparsing import Literal, Word, Optional, CaselessLiteral, Group, StringStart, StringEnd, Suppress, ParseResults, CharsNotIn, Forward, nums, delimitedList, operatorPrecedence, opAssoc

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
    column = Group(Suppress('[') + CharsNotIn(']') + Suppress(']') ).setParseAction(column_parse)
    expr = Forward()
    function_name = ( CaselessLiteral("SUM") | CaselessLiteral("AVG") | CaselessLiteral("MAX")
            | CaselessLiteral("MIN") | CaselessLiteral("BEST") )
    function = Group(function_name + Suppress('(') + delimitedList(expr) + Suppress(')')).setParseAction(func_parse)
    operand = number | column | function

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

def parse(expr):
    """
    Parse expression and return parse tree.
    """
    return parser.parseString(expr)[0]

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

def visible_grade(act, member):
    """
    Return student-visible grade on this activity
    """
    if act.status != 'RLS':
        return 0.0
    grades = act.numericgrade_set.filter(member=member)
    if len(grades)==0:
        return 0.0
    grade = grades[0]
    if grade.flag == 'NOGR':
        return 0.0
    else:
        return float(grade.value)
    

def eval_parse(tree, act_dict, member):
    """
    Evaluate an expression given its parse tree and dictionary of column values.
    
    Throws EvalException if there's a problem with the expression tree.
    
    Throws KeyError for unknown column.
    """
    t = tree[0]
    if t == 'sign' and tree[2] == '+':
        return eval_parse(tree[3], act_dict, member)
    elif t == 'sign' and tree[2] == '-':
        return -eval_parse(tree[3], act_dict, member)
    elif t == 'col':
        act = act_dict[tree[2]]
        part = tree[3]
        if part=="val":
            return visible_grade(act, member)
        elif part=="max":
            return float(act.max_grade)
        elif part=="per":
            if act.percent:
                return float(act.percent)
            else:
                return 0.0
        elif part=="fin":
            if act.percent:
                grade = visible_grade(act, member)
                return grade/float(act.max_grade) * float(act.percent)
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
        val = eval_parse(expr.pop(), act_dict, member)
        while expr:
            # extract operator/operand pairs until they're all gone
            operator = expr.pop()
            operand = eval_parse(expr.pop(), act_dict, member)
            if operator == "+":
                val += operand
            elif operator == "-":
                val -= operand
            elif operator == "*":
                val *= operand
            elif operator == "/":
                val /= operand
            else:
                raise EvalException, "Unknown operator in parse tree: %s"%(operator,)
        return val
    elif t == 'func':
        func = tree[2]
        if func == 'SUM':
            return sum(eval_parse(t, act_dict, member) for t in tree[3:])
        elif func == 'MAX':
            return max(eval_parse(t, act_dict, member) for t in tree[3:])
        elif func == 'MIN':
            return min(eval_parse(t, act_dict, member) for t in tree[3:])
        elif func == 'AVG':
            return sum(eval_parse(t, act_dict, member) for t in tree[3:]) / (len(tree)-3)
        elif func == 'BEST':
            # round first argument to an int: it's the number of best items to pick
            n = int(round( eval_parse(tree[3], act_dict, member) ) + 0.1)
            if n < 1:
                raise EvalException, 'Bad number of "best" selected, %i.'%(n,)
            if n > len(tree)-4:
                raise EvalException, "Not enough arguments to choose %i best."%(n,)
            marks = [eval_parse(t, act_dict, member) for t in tree[4:]]
            marks.sort()
            return sum(marks[-n:])
        else:
            raise EvalException, "Unknown function in parse tree: %s"%(func,)
    else:
        raise EvalException, "Unknown element in parse tree: %s"%(tree,)
    

