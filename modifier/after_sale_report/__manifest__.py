# -*- coding: utf-8 -*-
{
    'name': "After Sales Report",

    'summary': """
    After Sales Report
    """,

    'author': "Ridho",
    'license': 'OPL-1',
    'category': 'Tools',
    'version': '1.1.1',

    'depends': [
        'base',
        # 'report_xlsx',
        'web',
        'after_sales_service',
    ],

    'data': [
        'security/ir.model.access.csv',

        'reports/after_sales_operation_report_wizard.xml',
        'reports/service_request_report.xml',
        'reports/technician_task_report_wizard.xml',
        'reports/technician_task_report_wizard_template.xml',

        'views/after_sales_report_menu.xml',
    ],

    'external_dependencies': {
        'python': ['xlsxwriter'],
    },

}
