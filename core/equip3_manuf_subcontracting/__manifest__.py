# -*- coding: utf-8 -*-

{
    "name": "Equip 3 - Manufacturing Subcontracting",
    "version": "1.1.11",
    "category": "Manufacturing",
    "summary": "Manufacturing Subcontracting",
    "description": """
    1. Production Subcontracting
    2. Production Subcontracting Valuations
    """,
    "author": "HashMicro / Rajib",
    "website": "www.hashmicro.com",
    "depends": [
        "mrp_subcontracting",
        "equip3_purchase_other_operation",
        "equip3_manuf_account"
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/mrp_subcontracting_data.xml",
        "views/mrp_bom_views.xml",
        "views/mrp_consumption_views.xml",
        "views/mrp_cost_actualization_views.xml",
        "views/mrp_production_views.xml",
        "views/mrp_workorder_views.xml",
        "views/purchase_order_views.xml",
        "views/purchase_request_views.xml",
        "views/purchase_requisition_views.xml",
        "views/res_config_settings_views.xml",
        "views/stock_picking_views.xml",
        "views/stock_valuation_layer_views.xml",
        "wizard/make_purchase_order_views.xml",
        "wizard/mrp_subcontracting_wizard_views.xml",
        "wizard/requisition_delivery_order_views.xml"
    ],
    "qweb": [
    ],
    "installable": True,
    "application": True,
    "auto_install": False
}
