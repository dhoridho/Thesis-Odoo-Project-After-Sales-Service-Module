# -*- coding: utf-8 -*-
{
    'name': "Property Management Operation Asset",
    'summary': "Property Management Operation Asset",
    'description': "Property Management Operation Asset",
    'author': "Hashmicro",
    'website': "https://www.hashmicro.com",
    'category': 'Sales',
    'version': '1.1.2',
    'depends': ['base', 'property_rental_mgt_app', 'equip3_asset_fms_operation'],
    'data': [
        # 'security/ir.model.access.csv',
        'views/property_menu.xml',
        'views/maintenance.xml',
        'views/property.xml',
        'wizard/create_work_order.xml',
    ],
    'application': True,
}
