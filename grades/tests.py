from django.test import TestCase
from grades.formulas import *
import pickle

expr_vals = { # dictionary of assignment marks for formula testing
    'A1': 10,
    'A2': 30,
    'Assignment #1': 10,
    u"\u00b6": 4.5
    }
test_formulas = [ # expression, correct-result pairs
        ("9 + 2 - 3", 8),
        ("9 + 2 * 3", 15),
        ("(9 + 2) * 3", 33),
        ("-[A1] + +2", -8),
        ("[A1]/20+-3", -2.5),
        ("[Assignment #1]/20+-3", -2.5),
        ("SUM(1, 12.5, 3.4e2)", 353.5),
        ("SUM([A1]*2,[A2]/2)", 35),
        ("MAX([A1],[A2])", 30),
        ("max([A1],[A2])", 30),
        ("Min([A1],[A2], 12)", 10),
        ("AVG([A1],[A2], 12)", 17.3333333333333),
        (u"BEST(2, [A1], [A2])", 40),
        (u"BEST(2, [A1], [\u00b6],[A2], 12,-123)", 42),
        (u"BEST(3, [A1], [\u00b6],[A2], 12,123   )  ", 165),
        (u"[\u00b6] + 1", 5.5),
        ]

class GradesTest(TestCase):
    def setUp(self):
        pass

    def test_formulas(self):
        """
        Test the formula parsing & evaluation.
        """
        # make sure a formula can be pickled and unpickled safely (i.e. can be cached)
        tree = parse("sum([Assignment #1], [A1], [A2])/20*-3")
        p = pickle.dumps(tree)
        tree2 = pickle.loads(p)
        self.assertEqual(tree, tree2)
        # check that it found the right list of columns used
        self.assertEqual(cols_used(tree), set(['A1', 'A2', 'Assignment #1']))
        
        # test parsing and evaluation to make sure we get the right values out
        for expr, correct in test_formulas:
            tree = parse(expr)
            res = eval_parse(tree, expr_vals)
            self.assertAlmostEqual(correct, res, msg=u"Incorrect result for %s"%(expr,))

        # test some badly-formed stuff for appropriate exceptions
        tree = parse("1 + BEST(3, [A1], [A2])")
        self.assertRaises(EvalException, eval_parse, tree, expr_vals)
        tree = parse("1 + BEST(0, [A1], [A2])")
        self.assertRaises(EvalException, eval_parse, tree, expr_vals)
        tree = parse("[Foo] /2")
        self.assertRaises(KeyError, eval_parse, tree, expr_vals)
        tree = parse("[a1] /2")
        self.assertRaises(KeyError, eval_parse, tree, expr_vals)
        
        self.assertRaises(ParseException, parse, "AVG()")
        self.assertRaises(ParseException, parse, "(2+3*84")
        self.assertRaises(ParseException, parse, "2+3**84")
        self.assertRaises(ParseException, parse, "AVG(2,3,4")


