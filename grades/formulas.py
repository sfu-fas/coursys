# based on http://pyparsing.wikispaces.com/file/view/simpleArith.py
# and http://pyparsing.wikispaces.com/file/view/simpleSQL.py

# Usual usage of the parser:
#   from grades.formulas import *
# for each calculated grade:
#   parsed_expr = parse(formula)
# for each student, create a dictionary of assignment values:
#   vals = {'Assign 1': 23, 'Midterm': 89}
# then pass it into the evaluator:
#   result = eval_parse(parsed_expr, vals):

from external.pyparsing import ParseException

class EvalException(Exception):
    pass

def create_parser():
    """
    Build and return a parser for expressions.
    
    Parser builds a tuple-based representation of the formula the should be easy to evaluate.
    Each component is a tuple with the first element indicating the type, and the rest giving
    the required arguments for the formula-chunk.
    
    Parser throws ParseException if something goes wrong.
    """
    from external.pyparsing import Literal, Word, Optional, CaselessLiteral, Group, StringStart, StringEnd, Suppress, ParseResults, CharsNotIn, Forward, nums, delimitedList, operatorPrecedence, opAssoc

    def column_parse(toks):
	return ("col", toks[0][0])

    def real_parse(toks):
	return ("num", float(''.join(toks)))

    def func_parse(toks):
	return ("func",) + tuple(toks[0])

    def expr_parse(s, loc, toks):
        ts = toks[0]
        if len(ts) == 2:
            # unary operator
            return ("sign",) + tuple(toks[0])
        elif len(ts) > 1 and len(ts)%2==1:
            # one or more ops at the same level
            return ("expr",) + tuple(toks[0])
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

def eval_parse(tree, vals):
    """
    Evaluate an expression given its parse tree and dictionary of column values.
    
    Throws EvalException if there's a problem with the expression tree.
    
    Throws KeyError for unknown column.
    """
    t = tree[0]
    if t == 'sign' and tree[1] == '+':
        return eval_parse(tree[2], vals)
    elif t == 'sign' and tree[1] == '-':
        return -eval_parse(tree[2], vals)
    elif t == 'col':
        return float(vals[tree[1]])
    elif t == 'num':
        return tree[1]
    elif t == 'expr':
        expr = list(tree)
        expr.reverse()
        expr.pop() # remove the 'expr' marker
        # extract first term
        val = eval_parse(expr.pop(), vals)
        while expr:
            # extract operator/operand pairs until they're all gone
            operator = expr.pop()
            operand = eval_parse(expr.pop(), vals)
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
        func = tree[1]
        if func == 'SUM':
            return sum(eval_parse(t, vals) for t in tree[2:])
        elif func == 'MAX':
            return max(eval_parse(t, vals) for t in tree[2:])
        elif func == 'MIN':
            return min(eval_parse(t, vals) for t in tree[2:])
        elif func == 'AVG':
            return sum(eval_parse(t, vals) for t in tree[2:]) / (len(tree)-2)
        elif func == 'BEST':
            # round first argument to an int: it's the number of best items to pick
            n = int(round( eval_parse(tree[2], vals) ) + 0.1)
            if n < 1:
                raise EvalException, 'Bad number of "best" selected, %i.'%(n,)
            if n > len(tree)-3:
                raise EvalException, "Not enough arguments to choose %i best."%(n,)
            vals = [eval_parse(t, vals) for t in tree[3:]]
            vals.sort()
            return sum(vals[-n:])
        else:
            raise EvalException, "Unknown function in parse tree: %s"%(func,)
    else:
        raise EvalException, "Unknown element in parse tree: %s"%(tree,)
    

