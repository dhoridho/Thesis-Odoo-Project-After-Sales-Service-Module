# -*- coding: utf-8 -*-

{
    "name": "Equip 3 - Manufacturing Account",
    "version": "1.1.25",
    "category": "Manufacturing",
    "summary": "Manufacturing Account",
    "description": """
    1. Production Analytics
    2. Production Valuations
    3. Production Cost Actualization
    4. Workcenter Asset
    """,
    "author": "HashMicro / Rajib",
    "website": "www.hashmicro.com",
    "depends": [
        "mrp_account",
        "equip3_manuf_operations_contd",
        "equip3_accounting_analytical",
        "om_account_asset"
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "data/ir_sequence_data.xml",
        "views/assets.xml",
        "views/mrp_bom_views.xml",
        "views/mrp_consumption_views.xml",
        "views/mrp_cost_actualization_views.xml",
        "views/mrp_plan_views.xml",
        "views/mrp_production_views.xml",
        "views/mrp_workcenter_views.xml",
        "views/mrp_workorder_views.xml",
        "views/product_category_views.xml",
        "views/stock_move_views.xml",
        "views/stock_valuation_layer_views.xml",
        "views/product_template_views.xml",
        "reports/mrp_report_bom_structure_inherit.xml",
        "reports/report_mrp_bom_line_inherit.xml",
        "wizard/mrp_flexible_consumption_warning_views.xml",
        "views/mrp_menuitems.xml"
    ],
    "qweb": [
    ],
    "installable": True,
    "application": True,
    "auto_install": False
}
