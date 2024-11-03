# -*- coding: utf-8 -*-
{
    'name': "Property Management Report Contract",
    'summary': "Property Management Report Contract",
    'description': "Property Management Report Contract",
    'author': "My Company",
    'website': "https://www.hashmicro.com/",
    'category': 'Sales',
    'version': '1.1.1',
    'depends': ['base','membership','account', 'product', 'property_rental_mgt_app'],
    'data': [
        # 'security/ir.model.access.csv',
        'views/property_pivot.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'installable' : True,
    'auto_install' : False,
    'application' : True,
}
