# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip 3 - Manufacturing Other Operations',
    'author': 'Hashmicro',
    'version': '1.2.13',
    'category': 'Manufacturing',
    'summary': 'Manufacturing Other Operations',
    'description': '''
    1. Finished Goods Simulations
    ''',
    'author': 'HashMicro / Rajib',
    'website': 'www.hashmicro.com',
    'depends': [
        'equip3_manuf_operations_contd'
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'data/ir_sequence_data.xml',
        'views/assets.xml',
        'views/fg_simulation_views.xml',
        'views/mrp_mps_views.xml',
        'views/mrp_mps_old_views.xml',
        'views/mps_production_views.xml',
        'views/mrp_plan_views.xml',
        'views/mrp_production_views.xml',
        'views/mrp_workcenter_views.xml',
        'wizard/mps_detail_views.xml',
        'wizard/mrp_mps_detail_views.xml',
        'views/mrp_menuitems.xml',
    ],
    'qweb': [
        "static/src/xml/mrp_mps.xml",
        "static/src/xml/mrp_mps_replenish.xml",
        "static/src/xml/mps_widget.xml",
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}
