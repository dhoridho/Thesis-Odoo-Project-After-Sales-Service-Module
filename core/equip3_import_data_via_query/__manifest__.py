# -*- coding: utf-8 -*-
{
    'name': "Import Data Via Query",

    'summary': """
        This module helps to import purchase orders , pos order , account move, product, records """,

    'description': """
        
    """,
    'author': "Hashmicro/Balaji",
    'website': "http://www.hashmicro.com",
    'category': 'purchase',
    'version': '1.1.2',
    'depends': ['base','purchase','sale','point_of_sale','equip3_inventory_masterdata', 'equip3_sale_purchase', 'account','purchase_stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/import_record_sequence.xml',
        'views/import_data_view.xml',
    ],
    'application': True,
    'installable': True,
    'demo': [],
}
