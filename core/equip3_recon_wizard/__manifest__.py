# -*- coding: utf-8 -*-

{
     'name': 'Bank Reconciliation Wizard',
    'version': '1.0.1',
    'summary': 'Manual Bank Reconciliation',
    'description': """
    Manual Bank Reconciliation
    """,
    'author': 'HashMicro',
    'images': ['static/description/banner.gif'],
    'website': 'https://www.hashmicro.com',
    'maintainer': 'Hashmicro',
    'category': 'Accounting',
    'license': 'LGPL-3',


    'depends': [
        'base', 'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/reconcile.xml',
        'views/manual_recon.xml',
    ],
    'assets': {
        'equip3_recon_wizard.reconcileAsset': [
            'equip3_recon_wizard/static/*/*.js',
            'equip3_recon_wizard/static/*/*.css',

        ],
    },

}
