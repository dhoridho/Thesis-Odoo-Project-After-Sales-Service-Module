# -*- coding: utf-8 -*-
{
    'name': 'Quotation Revision',
    'author': 'Aktiv Software',
    'category': 'sales',
    'license': 'AGPL-3',
    'website': 'www.aktivsoftware.com',
    'version': '1.1.1',
    'summary': '''
                Quotation Revised History
            ''',
    'description': '''
                    We can manage Quotation Revised History in sale order.
                ''',
    'depends': ['sale_management'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'images': [
        'static/description/banner.jpg',
    ],
    'installable': True,
    'auto_install': False,
    'application': False
}
