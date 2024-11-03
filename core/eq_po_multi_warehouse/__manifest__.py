# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright 2019 EquickERP
#
##############################################################################

{
    'name': "Purchase Multi Picking",
    'version': '1.1.2',
    'category': 'Purchases',
    'author': 'Equick ERP',
    'summary': """purchase order multi picking | po multi picking | purchase multi picking | operation type on purchase order line | deliver to selection on purchase order line | deliver to on purchase order line | po multi incoming shipping | po multi receipt""",
    'description': """
        Purchases Multi Picking
        * Allow user to select different warehouse on purchases order line.
        * Generate Delivery orders based on the warehouse selected.
        * User can see the warehouse on Pdf Report, purchases analysis report, Customer portal view.
    """,
    'license': 'OPL-1',
    'depends': ['purchase', 'purchase_stock'],
    'price': 14,
    'currency': 'EUR',
    'website': "",
    'data': [
        'views/purchase_view.xml',
        'views/purchase_report_template.xml'
    ],
    'images': ['static/description/main_screenshot.png'],
    'installable': True,
    'auto_install': False,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: