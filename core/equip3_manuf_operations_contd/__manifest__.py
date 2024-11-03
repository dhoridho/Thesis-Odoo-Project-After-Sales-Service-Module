# -*- coding: utf-8 -*-

{
    'name': 'Equip 3 - Manufacturing Operations Continued',
    'version': '1.1.82',
    'category': 'Manufacturing',
    'summary': 'Manufacturing Operations Continued',
    'description': '''
    1. Production Record
    2. Production Record Approval Matrix
    3. Transfer Back Material
    ''',
    'author': 'HashMicro / Rajib',
    'website': 'www.hashmicro.com',
    'depends': [
        "equip3_manuf_operations",
        "equip3_inventory_scale"
    ],
    'data': [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "data/ir_sequence_data.xml",
        "data/on_upgrade.xml",
        "views/mrp_consumption_view.xml",
        "views/mrp_workorder_view.xml",
        "views/mrp_production_views.xml",
        "views/mrp_plan_views.xml",
        "views/mrp_approval_matrix.xml",
        "views/mrp_bom_views.xml",
        "views/res_config_settings_views.xml",
        "views/mrp_menuitems.xml",
        "wizards/mrp_flexible_consumption_warning_views.xml",
        "wizards/button_mark_done_warning_views.xml"
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_load': '_monkey'
}
