{
    "name": "Singapore HR Reports",
    "version": "14.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["l10n_sg_hr_payroll", "sg_hr_holiday"],
    "sequence": 1,
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "maintainer": "Serpent Consulting Services Pvt. Ltd.",
    "website": "http://www.serpentcs.com",
    "category": "Human Resources",
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
    """,
    'data': ['security/ir.model.access.csv',
             'views/external_layout_report.xml',
             'views/payslip_report.xml',
             'views/payslip_voucher_template.xml',
             'views/hr_bank_summary_template.xml',
             'views/cheque_summary_report_temp.xml',
             'views/hr_payroll_summary_temp.xml',
             'views/sg_hr_report_menu.xml',
             'wizard/upload_xls_wizard_view.xml',
             'wizard/payroll_summary_wizard_view.xml',
             'wizard/cpf_payment_wizard_view.xml',
             'wizard/bank_summary_wizard_view.xml',
             'wizard/cheque_summary_report_view.xml',
             "wizard/export_employee_summary_wiz_view.xml",
             'wizard/cpf_rule_text_file_view.xml',
             'wizard/payroll_generic_summary_wiz.xml'],
    'installable': True,
    'auto_install': False,
    'application': True,
    "price": 149,
    "currency": 'EUR',
}
