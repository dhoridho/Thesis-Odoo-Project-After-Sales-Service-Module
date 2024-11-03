# -*- coding: utf-8 -*-
{
    'name': "equip3_accounting_opening_balance",
    'version': '1.1.4',
    'category': 'Accounting',
    'author': 'Eka Nuryanti',
    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",
    'description': """
        Long description of module's purpose
    """,


    'website': "http://www.yourcompany.com",


    # any module necessary for this one to work correctly
    'depends': ['account', 'equip3_accounting_operation'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/partner_opening_balance.xml',
        'wizard/opening_balance.xml',
        
    ],
    'installable': True,
    'auto_install': False,
}
