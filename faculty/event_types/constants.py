from faculty.event_types.choices import Choices

PERMISSION_CHOICES = {
    # who can create/edit/approve various things?
    'MEMB': 'Faculty Member',
    'DEPT': 'Department',
    'FAC': 'Dean\'s Office',
}
PERMISSION_LEVEL = {
    'NONE': 0,
    'MEMB': 1,
    'DEPT': 2,
    'FAC': 3,
}

EVENT_FLAGS = [
    'affects_teaching',
    'affects_salary',
    # You should add new flags just above this line
]

SALARY_STEPS_CHOICES = Choices(
    ('-', 'Pending'),
    ('0.0', '0.0'),
    ('0.5', '0.5'),
    ('1.0', '1.0'),
    ('1.5', '1.5'),
    ('2.0', '2.0'),
    ('2.5', '2.5'),
    ('3.0', '3.0'),
)
