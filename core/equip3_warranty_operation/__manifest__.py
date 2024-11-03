# -*- coding: utf-8 -*-
{
    'name': "equip3_warranty_operation",
    'summary': "Warranty Operation",
    'description': "Warranty Operation",
    'author': "PT. HasMicro Pte Ltd",
    'website': "http://www.hashmicro.com",
    'category': 'inventory',
    'version': '1.1.1',
    'depends': ['base','bi_warranty_registration','equip3_inventory_operation','equip3_inventory_masterdata'],
    'data': [
        # 'security/ir.model.access.csv',
        'data/asset.xml',
        'views/product_views.xml',
        'views/product_warranty_views.xml',
    ],
}
