{
    'name': 'Accounting Analytical',
    'version': '2.1.6',
    'category' : 'Extra Tools',
    'depends': [
        'account',
        'analytic',
        'branch',
    ],
    'depends': ['account', 'analytic', 'branch','equip3_general_setting'],
    'data': [
        'security/ir.model.access.csv', 
        'data/data.xml',
        'views/account_analytic_tag_views.xml',
        'views/inherit_account_analytic_tag_views.xml', 
    ],
    'demo': [],
    'auto_install': False,
    'installable': True,
    'application': True
}