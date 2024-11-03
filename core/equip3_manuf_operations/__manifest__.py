# -*- coding: utf-8 -*-

{
    "name": "Equip 3 - Manufacturing Operations",
    "version": "1.4.26",
    "category": "Manufacturing",
    "summary": "Manufacturing Operations",
    "description": """
    i. Manufacturing Plan
    ii. Manufacturing Plan
    iii. Work Order
    iv. Auto Generate Internal Transfers on Manufacturing Plan/ Manufacturing Order/ Work Order
    v. Auto Generate Purchase Requeston Manufacturing Plan/ Manufacturing Order/ Work Order
    viii. Approval Matrix on Manufacturing Plan/ Manufacturing Order
    """,
    "author": "HashMicro / Rajib",
    "website": "www.hashmicro.com",
    "depends": [
        "ks_gantt_view_mrp",
        "app_mrp_superbar",
        "app_web_superbar",
        "acrux_chat_chatapi",
        "equip3_general_features",
        "equip3_manuf_masterdata"
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "data/ir_sequence_data.xml",
        "views/assets.xml",
        "views/mrp_approval_matrix.xml",
        "views/mrp_approval_matrix_entry_views.xml",
        "views/mrp_plan.xml",
        "views/mrp_production_view.xml",
        "views/mrp_workorder_view.xml",
        "views/mrp_workcenter_views.xml",
        "views/product_template_views.xml",
        "views/stock_move_view.xml",
        "views/stock_picking_views.xml",
        "views/mrp_routing_operations_views.xml",
        "views/mrp_routing_views.xml",
        "views/mrp_unbuild_views.xml",
        "views/res_config_settings_views.xml",
        "views/mrp_menuitems.xml",
        "wizard/mrp_plan_add_manufacturing_wiz.xml",
        "wizard/mrp_plan_change_component_wiz.xml",
        "wizard/mrp_reserve_material_views.xml",
        "wizard/mp_done_confirm_wiz.xml",
        "wizard/mrp_approval_matrix_reject_views.xml",
        "wizard/mrp_plan_line_wizard_views.xml",
        "templates/mail_template_reuse.xml"
    ],
    "qweb": [
        "static/src/xml/free_widget.xml"
    ],
    "installable": True,
    "application": True,
    "auto_install": False
}
