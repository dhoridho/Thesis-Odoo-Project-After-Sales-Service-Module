{
    "name": "Singapore - Employee Management",
    "version": "14.0.1.0.0",
    'license': 'LGPL-3',
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "maintainer": "Serpent Consulting Services Pvt. Ltd.",
    "sequence": 1,
    "website": "http://www.serpentcs.com",
    "category": "Human Resources",
    "description":
    '''
    Module to manage Employee information.
    ''',
    "depends": ["hr_contract"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/hr_employee_view.xml",
        "views/hr_configuration_view.xml",
        "report/employee_paperformat.xml",
        "report/employee_info_report_view.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": True,
    "price": 49,
    "currency": 'EUR',
}
