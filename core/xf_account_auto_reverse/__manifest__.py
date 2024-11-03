# -*- coding: utf-8 -*-
{
    'name': 'Auto-Reversing Journal Entries',
    'version': '1.0.1',
    'summary': """
    Scheduled auto-reversing for journal entries
    | Auto Reverse
    | Auto Refund
    | Schedule Reversing Journal Entries
    | Schedule Reverse Journal Entry
    | Posting General Journal Entries with Auto Reverse 
    | Auto Reversal of General Journal Entries
    | Auto Reverse Posted General Journals in Odoo
    """,
    'category': 'Accounting',
    'author': 'XFanis',
    'support': 'odoo@xfanis.dev',
    'website': 'https://xfanis.dev',
    'license': 'OPL-1',
    'price': 20,
    'currency': 'EUR',
    'description':
        """
Auto Reverse Posted General Journals in Odoo
============================================
This module helps to schedule auto reverse for posted journal entries.

Utilizing Auto-Reversing Journal Entries is quite easy to forget to manually 
reverse out certain entries at the beginning of new account period.

Auto-reversing journal entries are used to avoid errors in reporting 
in situations where some accrued revenue or expenses from one accounting period 
should not remain on the books in the next account period. 
        """,
    'data': [
        'views/account_move.xml',
        'data/cron_run_auto_reverse.xml',
    ],
    'depends': ['account'],
    'qweb': [],
    'images': [
        'static/description/xf_account_auto_reverse.png',
        'static/description/misc_account_move_form.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
