{
    "name": "Singapore Holiday Extension",
    "version": "14.0.1.0.0",
    "license": "LGPL-3",
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "maintainer": "Serpent Consulting Services Pvt. Ltd.",
    "website": "http://www.serpentcs.com",
    "sequence": 1,
    "category": "Human Resources",
    "description":
    '''
    Module to manage Employee information.
    ''',
    "depends": [
        "sg_hr_holiday",
        "sg_holiday_config"
    ],
    "data": [
        "data/cessation_date_schedular_view.xml",
        "data/leave_type_view.xml",
        "data/mail_template.xml",
        "report/emp_pub_holiday_report_view.xml",
        "views/hr_employee_view.xml",
        "views/hr_year_setting_view.xml",
        "views/hr_holiday_view.xml",
        "views/leave_structure_view.xml",
        "security/ir.model.access.csv",
        "wizard/multi_public_holiday_view.xml",
        "wizard/leave_summary_report_view.xml",
    ],
    'demo': ["demo/hr_leave_structure.xml"],
    "installable": True,
    "auto_install": False,
    "application": True,
    "price": 99,
    "currency": 'EUR',
}
