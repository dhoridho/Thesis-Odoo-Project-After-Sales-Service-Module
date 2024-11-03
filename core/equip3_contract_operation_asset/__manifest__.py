# -*- coding: utf-8 -*-
{
    'name': "Contract Operation Asset",
    'summary': "Contract Operation for Asset",
    'description': "Contract Operation for Asset",
    'author': "My Hashmicro",
    'website': "http://www.hashmicro.com",
    'category': 'Uncategorized',
    'version': '1.1.1',
    'application': True,
    'category': 'Partner',
    'depends': ['base','agreement', 'equip3_asset_fms_operation', 'agreement_legal'],
    'data': [
        # 'security/ir.model.access.csv',
        'views/agreement_view.xml',
        'views/maintenance_order_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
