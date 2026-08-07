TYPE_CHOICES = (
    ('INTERNAL', 'Internal'),
    ('EXTERNAL_SFU', 'External (paid through SFU)'),
    ('EXTERNAL_NON_SFU', 'External (not paid through SFU)'),
    ('BOTH', 'Both Internal and External'),
)

WORK_ELIGIBILITY_STATUS_CHOICES = (
    ('CANADIAN_CITIZEN', 'Canadian Citizen'),
    ('PERMANENT_RESIDENT', 'Permanent Resident'),
    ('INTERNATIONAL', 'International'),
)

WORK_HOURS_CHOICES = (
    ('FULL_TIME', 'Full Time (35 hours/week)'),
    ('PART_TIME', 'Part Time'),
    ('EXT', 'External'),
    ('LS', 'Lump Sum'),
)

DEPT_CHOICES = (
    ('', '-----------'),
    (2110, '2110 (CMPT)'),
    (2130, '2130 (ENSC)'),
    (2140, '2140 (MSE)'),
    (2150, '2150 (SEE)'),
    (2020, "2020 (Dean's Office)"),
    (2030, "2030 (Dean's Office)"),
)

FUND_CHOICES = (
    ('', '-----------'),
    (11, '11'), (13, '13'), (21, '21'), (23, '23'), (25, '25'), (29, '29'),
    (31, '31'), (32, '32'), (35, '35'), (36, '36'), (37, '37'), (38, '38'), (40, '40')
)

BOOL_CHOICES = (
    (True, 'Yes'), (False, 'No')
)

