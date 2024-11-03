{
    'name': 'Equip3 HR SG Reports',
    'version': '1.1.7',
    'author': 'Hashmicro / Diki',
    'website': "https://www.hashmicro.com",
    'category': 'HRM SG',
    'summary': """
    Added some new fields and overrided the list view.
    """,
    'depends': ['sg_hr_report'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/cpf_payment_wizard.xml',
        'wizard/cpf_return_checking_wizard.xml',
        'wizard/pay_history_wizard.xml',
        'wizard/payroll_variance_report_view.xml',
        'wizard/hr_attendance_report_wizard.xml',
        'wizard/hr_time_off_report_wizard.xml',

        'report/report.xml',
        'report/cpf_return_checking_report.xml',
        'report/ytd_payslip_report.xml',
        'report/payslip_report.xml',
        'report/pay_history_report.xml',
        'report/payroll_variance_report_tmp.xml',
        'report/payroll_variance_report.xml',
        'report/hr_attendance_report.xml',
        'report/hr_time_off_report.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
