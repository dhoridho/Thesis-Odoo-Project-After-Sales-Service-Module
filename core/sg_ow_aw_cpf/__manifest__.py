{
    "name": "SG CPF Extended",
    "version": "14.0.1.0.0",
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "sequence": 1,
    "description": """A module worked for cpf where allowances are divided in
    category of aw & ow similarly applied improve reports for ir8a & ir8s.""",
    "license": "LGPL-3",
    "website": "http://www.serpentcs.com",
    "depends": ["sg_income_tax_report", "sg_hr_payslip_YTD"],
    "category": "Generic Modules/SG Custom Features",
    "data": [
        'security/hr.salary.rule.category.csv',
        'views/sg_custom_view.xml',
        'views/ir8s_form_report_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
