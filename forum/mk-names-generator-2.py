#!/usr/bin/env python3

# After names.json is generated by mk-names-generator-1.go, this builds names_generator.py that is actually used by
# the system.
#   python3 mk-names-generator-2.py

OUTPUT_FILE = 'names_generator.py'
TEMPLATE = """# This file is generated by mk-names-generator-2.py. Probably don't edit it by hand.

# This code implements the same random name generation used for Docker containers, as found here:
# https://github.com/moby/moby/blob/master/pkg/namesgenerator/names-generator.go


import random
LEFT = %r
RIGHT = %r


def get_random_name() -> str:
    l = random.choice(LEFT)
    r = random.choice(RIGHT)
    if l == 'boring' and r == 'wozniak':
        # Steve Wozniak is not boring: try again
        return get_random_name()
    return l.title() + ' ' + r.title()
"""

NEGATIVES = [  # remove a few negative-sounding adjectives, to maximize positivity.
    'angry',
    'condescending',
    'cranky',
    'distracted',
    'naughty',
    'pedantic',
    'sad',
    'stupefied',
]

import json

names = json.load(open('names.json'))
left = [n for n in names['Left'] if n not in NEGATIVES]
right = names['Right']
with open(OUTPUT_FILE, 'wb') as fh:
    fh.write((TEMPLATE % (left, right)).encode('utf-8'))