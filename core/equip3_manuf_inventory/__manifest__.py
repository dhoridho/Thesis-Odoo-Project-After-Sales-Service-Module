# -*- coding: utf-8 -*-

{
    "name": "Equip 3 - Manufacturing Inventory",
    "version": "1.1.21",
    "category": "Manufacturing",
    "summary": "Manufacturing Inventory",
    "description": """
    1. Secret BoM
    2. Material Request
    3. Transfer Request
    4. Change Material
    """,
    "author": "HashMicro / Rajib",
    "website": "www.hashmicro.com",
    "depends": [
        "equip3_manuf_account",
        "equip3_inventory_control"
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/assets.xml",
        "views/internal_transfer_views.xml",
        "views/mrp_bom_views.xml",
        "views/mrp_consumption_views.xml",
        "views/mrp_plan_views.xml",
        "views/mrp_production_views.xml",
        "views/mrp_workorder_views.xml",
        "views/product_views.xml",
        "views/stock_warehouse_orderpoint_views.xml",
        "views/res_config_settings_views.xml",
        "wizard/mrp_material_request_wizard_views.xml",
        "views/stock_valuation_layer_views.xml"
    ],
    "qweb": [
    ],
    "installable": True,
    "application": True,
    "auto_install": False
}
