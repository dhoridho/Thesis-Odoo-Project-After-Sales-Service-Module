# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip 3 - Inventory Quality Control',
    'author': 'Coderlab Technology',
    'version': '1.1.24',
    'category': 'Inventory',
    'summary': 'Inventory Quality Control',
    'description': '''''',
    'depends': [
        'sh_inventory_mrp_qc',
        'equip3_inventory_operation',
        'equip3_hashmicro_ui',
        'web_domain_field',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/mail_templates.xml',
        'views/internal_transfer.xml',
        'views/repair_order_views.xml',
        'wizard/stock_global_check_views.xml',
        'views/quality_point_views.xml',
        'views/assets.xml',
        'views/checksheet_view.xml',
        'views/qc_answer_views.xml',
        'views/qc_items_views.xml',
        'views/product_template_views.xml',
        'views/stock_picking_views.xml',
        'views/quality_check_views.xml',
        'views/quality_alert_views.xml',
        'views/quality_check_readonly_views.xml',
        'views/quality_alert_readonly_views.xml',
        'views/picking_menu_action.xml',
        'views/inventory_qc_dashboard.xml',
        'views/menu_views.xml'
        
    ],
    "qweb": [
        "static/src/xml/web_widget_image_webcam.xml",
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}
