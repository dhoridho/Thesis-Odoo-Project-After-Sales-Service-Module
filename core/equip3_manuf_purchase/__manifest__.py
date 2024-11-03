# -*- coding: utf-8 -*-

{
    "name": "Equip 3 - Manufacturing Purchase",
    "version": "1.1.10",
    "category": "Manufacturing",
    "summary": "Manufacturing Purchase",
    "description": """
    1. Material Purchase Request
    2. Material To Purchase
    """,
    "author": "HashMicro / Rajib",
    "website": "www.hashmicro.com",
    "depends": [
        "purchase_mrp",
        "equip3_purchase_operation",
        "equip3_manuf_inventory"
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "data/ir_sequence_data.xml",
        "views/mrp_material_purchase_views.xml",
        "views/mrp_plan_views.xml",
        "views/mrp_production_views.xml",
        "views/mrp_workorder_views.xml",
        "views/purchase_request_views.xml",
        "views/res_config_settings_views.xml",
        "views/mrp_menuitems.xml"
    ],
    "qweb": [
    ],
    "installable": True,
    "application": True,
    "auto_install": False
}
