# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip3 Accounting Cash Advance',
    'version': '1.1.8',
    'author': 'Hashmicro / Arivarasan',
    'category': 'Accounting/Cash Advance',
    'depends': ['base', 'account', 'equip3_accounting_cash_advance','equip3_accounting_deposit'],
    'data': [
        'data/cash_advance_matrix_template.xml',
        'data/wa_cash_advance_template.xml',
        'security/ir.model.access.csv',
        'views/account_cash_advance.xml',
        'views/vendor_deposit_views.xml',
        'wizard/cash_advance_reject_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
