# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright 2019 EquickERP
#
##############################################################################

{
    'name': "Scrap Order Report",
    'category': 'Stock',
    'version': '14.0.2',
    'author': 'Equick ERP',
    'description': """
        This Module allows you to generate Scrap Order Report PDF/XLS wise.
        * Allows you to generate Scrap Order PDF/XLS Report.
        * Support with Multi Company.
        * Works with Lot/serial number.
    """,
    'summary': """ This Module allows you to generate Scrap Order Report PDF/XLS wise. scrap report | scrap order report. """,
    'depends': ['base', 'stock'],
    'price': 12,
    'currency': 'EUR',
    'license': 'OPL-1',
    'website': "",
    'data': [
        'security/ir.model.access.csv',
        'wizard/wizard_scrap_order_report_view.xml',
        'report/report.xml',
        'report/scrap_order_report.xml',
    ],
    'images': ['static/description/main_screenshot.png'],
    'installable': True,
    'auto_install': False,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: