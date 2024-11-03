# -*- coding: utf-8 -*-
{
    'name': "Account Stock Operation",

    'summary': """
    	Accounting Stock Operation
        """,

    'description': """
        For Configure and Provide Accounting Stock Operation
    """,

    'author': "Hashmicro / Febri Zummiati",
    'website': "https://www.hashmmicro.com",

    'category': 'accounting',
    'version': '12.7.5',

    'depends': [
    	'stock_account', 
    	'equip3_inventory_reports', 
    	'equip3_accounting_operation', 
    	'equip3_accounting_accessright_setting',
        'equip3_general_features',
        'bi_inter_company_transfer'
    	],

    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/product_views.xml',
    ],
    'demo': [],
    'auto_install': False,
    'installable': True,
    'application': True

}
