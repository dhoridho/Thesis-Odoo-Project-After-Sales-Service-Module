{
    "name": "Singapore Payroll",
    "version": "14.0.1.0.0",
    "depends": ["sg_holiday_extended", "l10n_sg", "scs_hr_payroll", "hr_contract",
                'account'],
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "website": "http://www.serpentcs.com",
    "maintainer": "Serpent Consulting Services Pvt. Ltd.",
    "category": "Localization",
    "license": "LGPL-3",
    "sequence": 1,
    "category": "Localization",
    "description": """
        Singapore Payroll Salary Rules.
        ============================

        -Configuration of hr_payroll for Singapore localization
        -All main contributions rules for Singapore payslip.
        * New payslip report
        * Employee Contracts
        * Allow to configure Basic / Gross / Net Salary
        * CPF for Employee and Employer salary rules
        * Employee and Employer Contribution Registers
        * Employee PaySlip
        * Allowance / Deduction
        * Integrated with Holiday Management
        * Medical Allowance, Travel Allowance, Child Allowance, ...

        - Payroll Advice and Report
        - Yearly Salary by Head and Yearly Salary by Employee Report
        - IR8A and IR8S esubmission txt file reports
    """,
    "summary": """
        Singapore Payroll Salary Rules.
        ============================

        -Configuration of hr_payroll for Singapore localization
        -All main contributions rules for Singapore payslip.
    """,
    'data': [
        'security/group.xml',
        'security/ir.model.access.csv',
        'data/hr_employee_category_data.xml',
        'data/hr_salary_rule_category_data.xml',
        'data/hr_contribution_register_data.xml',
        'data/emp_nationality_data.xml',
        'wizard/hr_payslip_by_employee_view.xml',
        'views/menu.xml',
        'data/salary_rule.xml',
        'data/hr_rule_input.xml',
        'views/payroll_extended_view.xml',
        'views/hr_contract_view.xml',
        'data/sg_data.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    "price": 149,
    "currency": 'EUR',
}
