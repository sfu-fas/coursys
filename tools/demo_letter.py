import os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.append('.')
sys.path.append('external')

from dashboard.letters import OfficialLetter, LetterContents
from coredata.models import Unit
import random

from django.contrib.webdesign.lorem_ipsum import paragraphs

def sample_letter():
    to_addr_lines = ['Some Person', '123 Fake St', 'Vancouver, BC, Canada']
    from_name_lines = ['Greg Baker', 'Lecturer, School of Computing Science']
    letter = LetterContents(to_addr_lines=to_addr_lines, from_name_lines=from_name_lines)
    letter.add_paragraphs(paragraphs(random.randint(5,20)))
    return letter

response = open("letter.pdf", "w")

unit = Unit.objects.get(label="CMPT")
doc = OfficialLetter(response, unit=unit)
doc.add_letter(sample_letter())
doc.add_letter(sample_letter())
doc.add_letter(sample_letter())
doc.write()




"""
unit.config = {u'address': [u'9971 Applied Sciences Building',
              u'8888 University Drive, Burnaby, BC',
              u'Canada V5A 1S6'],
 u'email': u'csdept@cs.sfu.ca',
 u'fax': u'778-782-3045',
 u'tel': u'778-782-4277',
 u'web': u'http://www.cs.sfu.ca'}
"""
