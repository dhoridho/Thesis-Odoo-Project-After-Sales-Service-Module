# -*- coding: utf-8 -*-

{
    "name": "Equip 3 - Manufacturing Cutting",
    "version": "1.1.6",
    "category": "Manufacturing",
    "summary": "Manufacturing Cutting",
    "description": """
    1. Cutting Order
    2. Cutting Plan
    3. Cutting Approval Matrix
    4. Cutting Whatsapp Notification
    5. Cutting Flow
    """,
    "author": "HashMicro / Rajib",
    "website": "www.hashmicro.com",
    "depends": [
        "equip3_manuf_operations",
        "equip3_accounting_analytical",
        "equip3_inventory_operation"
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "data/ir_sequence_data.xml",
        "templates/auto_mail_template.xml",
        "views/assets.xml",
        "views/cutting_order_line_views.xml",
        "views/cutting_order_views.xml",
        "views/cutting_plan_views.xml",
        "views/mrp_approval_matrix_views.xml",
        "views/product_views.xml",
        "views/res_config_settings_views.xml",
        "views/stock_move_views.xml",
        "views/stock_production_lot_views.xml",
        "views/menuitems.xml",
        "wizard/cutting_plan_add_cutting_views.xml"
    ],
    "qweb": [
        "static/src/xml/cutting_flow.xml"
    ],
    "installable": True,
    "application": True,
    "auto_install": False
}
