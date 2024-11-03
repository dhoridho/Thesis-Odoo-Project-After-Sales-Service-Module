{
    'name': 'Accounting Operation Extended',
    'version': '1.0.2',
    'category': 'Accounting',
    'author': 'Hashmicro',
    'depends': [
        'equip3_accounting_operation',
    ],
    'data': [
        'data/ir_sequence_data.xml',
        'security/ir.model.access.csv',
        'views/account_working_capital_views.xml',
        'views/account_voucher_views.xml',
        'views/account_payment_views.xml',
        'wizard/product_cost_adjusment_views.xml',
        # 'security/rule.xml',

        
    ],
    'demo': [],
    'auto_install': False,
    'installable': True,
    'application': True
}
