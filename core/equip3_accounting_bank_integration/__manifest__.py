{
    'name': 'Accounting Bank Integration',
    'version': '1.2.8',
    'category': 'Accounting',
    'author': 'Mochamad Rezki',
    'depends': [
        'account','branch','equip3_accounting_operation'
    ],
    'data': [
        'data/ir_sequence_data.xml',
        'data/account_data.xml',
        'data/res_bank_data.xml',
        'views/res_partner_view.xml',
        'views/account_statement.xml',
        'views/res_config_settings_views.xml',
        'views/account_payment_view.xml',
        'views/account_bank_statement_views.xml',
        'views/account_move_views.xml',
        'security/ir.model.access.csv',
        'wizard/generate_bank_statement_journal_wizard_views.xml',
    ],
    'demo': [],
    'auto_install': False,
    'installable': True,
    'application': True,
    # 'post_init_hook': 'post_init_hook',
    # 'uninstall_hook': 'uninstall_hook',
}