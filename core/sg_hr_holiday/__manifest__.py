{
    "name": "Singapore HR Holiday",
    "version": "14.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["sg_hr_employee", 'hr_holidays'],
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "maintainer": "Serpent Consulting Services Pvt. Ltd.",
    "sequence": 1,
    "website": "http://www.serpentcs.com",
    "category": "Human Resources",
    "description": """
        Singapore HR Holiday
        ============================
        * Manage types of Leaves.hr_contract
        * Manage Leaves Request and Allocation.
        * Manage Annual Leaves and Carry Forward Leaves
          Allocation By Schedulers.
    """,
    "summary": """Singapore HR Holiday""",
    'data': [
        "security/ir.model.access.csv",
        "view/hr_holiday_view.xml",
        "view/hr_leave_type_views.xml",
        "data/hr_holidays_schedular.xml",
        "data/hr_holiday_type.xml",
        "data/hr_holidays_email_template.xml",
        "report/employee_info_report_ext.xml",
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    "price": 49,
    "currency": 'EUR',
}
