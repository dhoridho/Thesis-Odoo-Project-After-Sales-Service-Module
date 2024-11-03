# -*- coding: utf-8 -*-
{
    'name': 'Description to Pickings(Shipment/Delivery)',
    'version': '14.0.2',
    'category': 'Inventory',
    'summary': 'This Module allows user to add product description on delivery and shipment order from sales and purchase'
               'and print moves description in picking reports or picking operation report',
    'description': """
      This Module allows user to add product description on delivery and shipment order 
      from sale order line and purchase.order.line 
      and to print those description on picking operation reports
""",
    'author': 'Abderrahmane ratib',
    'website': '',
    'depends': ['base', 'stock', 'sale_management', 'purchase'],
    'data': [
        'views/stock_view.xml',
        'report/stock_report_delivery.xml',
    ],
    'images': ['static/description/banner.png'],
    'live_test_url': "https://youtu.be/pLfTKlvIzNo",
    'installable': True,
    'application': True,
    'auto_install': False,
    'price': 15,
    'currency': 'EUR',
}
