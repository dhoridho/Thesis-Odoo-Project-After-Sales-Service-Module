# -*- coding: utf-8 -*-
{
    'name': "Recurring",

    'summary': """
        Recurring Invoices""",

    'description': """
        Long description of module's purpose
    """,

    'author': "AlFarkhan",
    'website': "http://hashmicro.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '1.2.26',
    'application': True,

    # any module necessary for this one to work correctly
    'depends': [
        
        'account',
        'sh_invoice_recurring',
        'equip3_accounting_operation',
        'equip3_general_setting',
        ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'report/invoice_recurring_report.xml',
        'views/recur_invoices_views.xml',
        'views/recur_account_payment_regist.xml',
        'views/recur_account_move.xml',
        'views/recur_account_payment.xml',
        'data/ir_sequence_data.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
