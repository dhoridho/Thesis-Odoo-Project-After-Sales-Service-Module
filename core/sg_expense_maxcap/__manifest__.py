{
    "name": "Hr Expense Maxcap",
    "version": "14.0.1.0.0",
    "license": "LGPL-3",
    "sequence": 1,
    "author": "Serpent Consulting Services Pvt. Ltd.",
    'category': 'Human Resources',
    "website": "http://www.serpentcs.com",
    "description": """
Manage Expense Reimbursement Maximum limit per Employee
========================================================
This module is used to add expense product and it's maximum amount limits
configurations in employee's contract,
which use in expense claim by user.

* Max cap to each expense product & facility to override the max cap on each
product for each employee.
""",
    "summary": """
Manage Expense Reimbursement Maximum limit per Employee
""",
    'depends': ['hr_contract', 'hr_expense'],
    'data': [
         'security/ir.model.access.csv',
         'view/hr_contract_view_extended.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    "price": 49,
    "currency": 'EUR',
}
