# coding: utf-8
from coredata.models import Unit
units = Unit.objects.get(label='UNI')
units.label = 'UNIV'
