# -*- coding: utf-8 -*-


{
    'name': 'Sales Management Enhancement',
    'version': '1.5',
    'category': 'Sales Management',
    'sequence': 14,
    'summary': 'Shop',
    'description': """
Manage sales shops
    """,
    'author': 'Pragmatic TechSoft Pvt Ltd',
    'website': 'www.pragtech.co.in',
    'images': [],
    'depends': ['sale','sale_stock','hotel'],
    'data': [
        'data/sale_data.xml',
        'views/sale_view.xml',
        'security/sale_security.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
