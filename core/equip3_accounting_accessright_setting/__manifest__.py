{
    'name': 'Accounting Access Right Setting',
    'version': '2.2.6',
    'category': 'Accounting',
    'author': 'Mochamad Rezki',
    'depends': [
        'account',
        'equip3_discount_with_tax',
        'equip3_general_setting',
        'app_account_superbar',
        'om_account_accountant',
        'base',
    ],
    'data': [        
        'security/accounting_security.xml',
        'security/ir.model.access.csv',
        'security/rule.xml',
        'views/config_views.xml',
        'views/multi_currency_config_views.xml',
        'views/sales_discount_config_settings.xml',
        'views/accounting_setting.xml',
        'views/res_config_settings_views.xml',
        'data/cash_advance_config.xml',
        'data/purchase_sale_account.xml',
        'views/accounting_menu_views.xml'
    ],
    'demo': [],
    'auto_install': False,
    'installable': True,
    'application': True
}
