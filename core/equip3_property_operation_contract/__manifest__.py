# -*- coding: utf-8 -*-
{
    'name': "Property Management Operation Contract",
    'summary': "Property Management Operation Contract",
    'description': "Property Management Operation Contract",
    'author': "Hashmicro",
    'website': "https://www.hashmicro.com",
    'category': 'Sales',
    'version': '1.1.1',
    'depends': ['base', 'property_rental_mgt_app'],
    'data': [
        'security/ir.model.access.csv',
        'views/property_menu.xml',
        'views/property.xml',
        'views/agreement.xml',
        'wizard/property_reserve.xml',
        'wizard/property_purchase.xml',
    ],
    'application': True,
}
