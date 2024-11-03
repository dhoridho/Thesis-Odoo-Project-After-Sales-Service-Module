# -*- coding: utf-8 -*-
{
    'name': "Blanket Sales Order App",
    'author': "Edge Technologies",
    'version' : '1.1.1',
    'live_test_url':'https://youtu.be/B6SZKtvT_8o',
    "images":["static/description/main_screenshot.png"],
    'summary': 'Blanket Sale Order manage blanket orders sale blanket orders for sales process sales agreement sale agreement sales blanket orders agreement orders seller agreement customer agreement order for customer agreement orders for sellers blanket order mass order',

    'description': """
      In this application you allows to create Blanket Sale Order. In that sales team create and manage blanket sales orders and allow them to create sales orders.
    """,
    
    'depends': ['base','sale_management','account'],
    "license" : "OPL-1",
    'data': [
    
    'security/ir.model.access.csv',
    'wizard/blanket_sale_wizard.xml',
    'data/sequence.xml',
    'views/sale_view.xml',
    

    
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'price':18,
    'currency': "EUR",
    'category' : 'Sales'
}
