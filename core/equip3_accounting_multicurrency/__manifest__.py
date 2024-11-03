{
    'name': 'Accounting Multicurrency',
    'version': '1.4.26',
    'category': 'Accounting',
    'author': 'Mochamad Rezki',
    'depends': [
        'equip3_accounting_accessright_setting',
        'equip3_accounting_operation',
        'sr_manual_currency_exchange_rate',
        'account',
        'aos_account_voucher',
        'equip3_accounting_masterdata',
        'branch',
        'om_account_budget',
        'om_account_asset',
        'sh_sync_fiscal_year',
        'equip3_discount_with_tax'
        # 'dev_purchase_down_payment'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/purchase_currency_approval_template.xml',
        'data/whatsapp_template.xml',
        'views/currency_views.xml',
        'views/account_move_views.xml',
        'wizards/currency_invoice_revaluation_views.xml',
        'wizards/account_register_payment.xml',
        'views/account_internal_transfer_views.xml',
        'data/ir_sequence_data.xml',
        'views/account_voucher_views.xml',
        'data/ir_cron.xml',
        'views/res_company_view.xml',
        'views/account_move_currency_views.xml',
    ],
    'demo': [],
    'auto_install': False,
    'installable': True,
    'application': True
}