# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip3 Rental Operation',

    'summary': 'Rental Operation Management',

    'description': """
        This module manages these features :
        1. Rental Orders
        2. Deposit
    """,

    'depends': [
        "browseinfo_rental_management",
        "general_template",
        'product', 
        'base',
        'mail',
        'barcodes', 
        'digest',
        'equip3_rental_masterdata',
        'equip3_hashmicro_ui',
        'equip3_inventory_operation',
        'equip3_inventory_reports',
    ],

    'author': "Hashmicro",
    'category': 'Rental',
    'version': '1.1.54',

    'data': [
        "security/ir.model.access.csv",
        'security/rental_rule.xml',
        "data/rental_new_sequence.xml",
        'data/cron.xml',
        'wizard/return_wizard.xml',
        "views/account_move_views.xml",
        "views/rental_extend_views.xml",
        "views/rental_order_views.xml",
        "report/report.xml",
        "report/checklist_template.xml",
        "report/report_rental_order.xml",
        "views/rental_menu_views.xml",
        'views/menu_category.xml',
        'views/product_template.xml',
        'views/rental_config_views.xml',
        'views/account_move_line.xml',
        'views/return_of_assets.xml',
        'wizard/cancel_rental_order_wizard.xml',
        'views/stock_picking_views.xml',
        'views/stock_move_views.xml',
        'views/rental_order_approval_matrix_views.xml',
        'wizard/rental_order_feedback_wizard.xml',
    ],
    'installable': True,   
}