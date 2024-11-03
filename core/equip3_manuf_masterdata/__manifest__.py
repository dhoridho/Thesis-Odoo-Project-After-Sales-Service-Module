# -*- coding: utf-8 -*-

{
    'name': 'Equip 3 - Manufacturing Master Data',
    'version': '1.1.65',
    'category': 'Manufacturing',
    'summary': 'Manufacturing Master Data',
    'description': '''
    i. Bill of Material (Manage Finished Products, Components, Operations, By-Product)
    ii. Work Center (Location Management, Overhead and OEE)
    ''',
    "author": "HashMicro / Rajib",
    "website": "www.hashmicro.com",
    'depends': [
        'branch',
        'mail',
        'equip3_manuf_accessright_settings',
        'mrp_workcenter_overview',
        'sh_all_in_one_mbs',
        'hr',
        'evo_bill_of_material_revised'
    ],
    'data': [
        'data/on_upgrade.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'view/mrp_workorder_views.xml',
        'view/mrp_workcenter_view.xml',
        'view/mrp_bom.xml',
        'view/mrp_routing_workcenter_views.xml',
        'view/mrp_workcenter_group.xml',
        'view/mrp_labor_group_views.xml',
        'view/res_config_settings_views.xml',
        'view/stock_production_lot_views.xml',
        'view/mrp_menuitems.xml',
        'view/product_template_views.xml',
        'templates/assets.xml',
    ],
    'demo': [],
    'qweb': [
        'static/src/xml/mrp.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}
