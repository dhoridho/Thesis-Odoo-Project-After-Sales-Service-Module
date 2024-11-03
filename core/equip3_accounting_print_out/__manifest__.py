# -*- coding: utf-8 -*-
{
    'name': "equip3_accounting_print_out",

    'summary': """""",

    'description': """
    """,

    'author': "Hashmciro",
    'website': "http://www.hashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'accounting',
    'version': '1.1.1',

    # any module necessary for this one to work correctly
    'depends': ['base','aos_account_voucher','web'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/report_payment_voucher_template.xml',
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
