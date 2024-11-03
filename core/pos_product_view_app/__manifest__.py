# -*- coding: utf-8 -*-

{
    'name' : 'POS Product List and Grid View App',
    'author': "Edge Technologies",
    'version' : '14.0.1.1',
    'live_test_url':'https://youtu.be/p0MIMGxlzRY',
    "images":["static/description/main_screenshot.png"],
    'summary' : 'POS Product List View POS product Grid View pos product view switch pos product switch view point of sales Product List View point of sales product Grid View point of sale product view switch point of sale product switch view point of sales product view',
    'description' : """

     This module helps to Display Point Of Sale Product in List View & Grid View.

    """,
    'depends' : ['base','point_of_sale',],
    "license" : "OPL-1",
    'data' : [
        'views/pos_product_view_config.xml',
        'views/assests.xml',
    ],
    'qweb': [
        'static/src/xml/pos_product_view.xml',
    ],

    'installable' : True,
    'auto_install' : False,  
    "price": 4.0,
    "currency": 'EUR',
    'category' : "Point of Sales",

}
