{
    "name": "Singapore YTD Payslip",
    "version": "14.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["l10n_sg_hr_payroll"],
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "website": "http://www.serpentcs.com",
    "sequence": 1,
    "category": "Localization",
    "summary": """Payslip's with YTD fields and its YTD Report""",
    "description": """
Singapore Payroll Report
Payslip report
year to date payslip details
payslip ytd
itemised payslip
    """,
    'data': [
        "views/payroll_extended_view.xml",
        "views/ytd_payslip_report_view.xml",
        "views/res_company_extended_view.xml",
        ],
    'installable': True,
    'auto_install': False,
    'application': True,
    "price": 29,
    "currency": 'EUR',
}
