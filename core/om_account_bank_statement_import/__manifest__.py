# -*- encoding: utf-8 -*-

{
    'name': 'Odoo 14 Account Bank Statement Import',
    'version': '1.1.3',
    'category': 'Accounting',
    'depends': ['account'],
    'website': 'https://www.odoomates.tech',
    'author': 'Odoo Mates, Odoo SA',
    'support': 'odoomates@gmail.com',
    'maintainer': 'Odoo Mates',
    'license': 'LGPL-3',
    'description': """Generic Wizard to Import Bank Statements In Odoo14 Community Edition.
(This module does include any CSV and XLSX type import format.)""",
    'data': [
        'security/ir.model.access.csv',
        'wizard/journal_creation.xml',
        'views/account_bank_statement_import_view.xml',
        'views/account_bank_statement_import_templates.xml',
    ],
    'demo': [
        'demo/partner_bank.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install': True,

    'routes': [
        {'name' : ' Download Template', 'url' : 'om_account_bank_statement_import/static/src/xlsx/bank_statement_import_template.xlsx', 'type' : 'http'},
    ],
}
