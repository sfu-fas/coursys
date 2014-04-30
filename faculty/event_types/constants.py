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
