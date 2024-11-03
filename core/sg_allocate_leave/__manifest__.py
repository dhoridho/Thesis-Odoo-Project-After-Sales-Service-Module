{
    "name": "Allocate Leave",
    "version": "14.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["sg_holiday_extended"],
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "maintainer": "Serpent Consulting Services Pvt. Ltd.",
    "website": "http://www.serpentcs.com",
    "sequence": 1,
    "category": "Human Resources",
    "description": """
Human Resource
============================
Add or Remove different types of leave to employee
allocate annual leaves based on leave structure
    """,
    'data': [
        'security/ir.model.access.csv',
        'wizard/allocate_leave_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    "price": 29,
    "currency": 'EUR',
}
