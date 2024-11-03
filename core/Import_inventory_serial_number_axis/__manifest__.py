# -*- coding: utf-8 -*-
{
    'name': 'Import Inventory Stock in odoo with Serial and Import Lot Number in odoo from Excel/CSV in Odoo Apps',
    'category': 'Import Record',
    'version': '13.0.0.0.0',
    'summary': "Import inventory, Import stock inventory adjustment, import product stock, import serial number in odoo inventory, import Lot Number in odoo, import Product barcode, code, name in odoo 14, odoo 13, odoo 12 and odoo 11",
    'depends': ['base','stock',],
    'data': [  
        'security/ir.model.access.csv',
        'wizard/import_inventory_adjustment_view.xml',
        'views/customer_menu.xml',
         
    ],
    'demo': [
    ],
    'price': 20,
    'currency': 'USD',
    'support': 'business@axistechnolabs.com',
    'author': 'Axis Technolabs',
    'website': 'http://www.axistechnolabs.com',
    'installable': True,
    'license': 'AGPL-3',
    'images': ['static/description/images/Banner-Img.png'],
}
