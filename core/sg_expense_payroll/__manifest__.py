{
    "name": "SG Expense Payroll",
    "version": "14.0.1.0.0",
    "license": "LGPL-3",
    "sequence": 1,
    "depends": ['l10n_sg_hr_payroll', 'hr_expense'],
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "website": "http://www.serpentcs.com",
    "category": "Human Resources",
    "description": """
        Expense auto calculation.
        =========================
        This modules will help for expenses auto calculation
        expense reimbursement in salary
        pay expense in salary
        expense payroll
        payroll auto expense rule
        expense reimbursement""",
    "summary": """Expense auto calculation.""",
    'data': [
        'security/ir.model.access.csv',
        'data/salary_rule.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    "price": 49,
    "currency": "EUR",
}
