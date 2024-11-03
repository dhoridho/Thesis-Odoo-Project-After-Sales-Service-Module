# -*- coding: utf-8 -*-
{
    'name': 'Equip3 - POS Membership - Indonesia',
    'author': 'Hashmicro',
    'version': '1.1.1',
    'summary': 'Indonesia - POS Membership & Loyalty',
    'depends': ['l10n_id_efaktur', 'equip3_pos_membership'],
    'category': 'POS',
    'data': [
        'views/account_move_views.xml',
        'views/pos_generate_efaktur_views.xml',
        'views/res_partner_views.xml',
    ],
    'qweb': [ 
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}