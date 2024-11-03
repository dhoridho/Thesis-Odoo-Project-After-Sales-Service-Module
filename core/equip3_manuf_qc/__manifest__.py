# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip 3 - Manufacturing Quality Control',
    'author': 'Hashmicro',
    'version': '1.1.14',
    'category': 'Manufacturing',
    'summary': 'Manufacturing Quality Control',
    'description': '''''',
    'author': 'HashMicro / Rajib',
    'website': 'www.hashmicro.com',
    'depends': [
        'equip3_manuf_operations_contd',
        'equip3_inventory_qc'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/mrp_bom_views.xml',
        'views/mrp_plan_views.xml',
        'views/mrp_production_views.xml',
        'views/mrp_workorder_views.xml',
        'views/mrp_consumption_views.xml',
        'views/quality_alert_views.xml',
        'views/quality_point_views.xml',
        'views/mrp_quality_alert.xml',
        'views/mrp_quality_check.xml',
        'views/sh_qc_views.xml',
        'views/sh_qc_actions.xml',
        'views/sh_qc_menuitems.xml',
        'views/mrp_qc_wizard_views.xml',
        'views/inventory_views.xml',
        'wizard/mrp_qa_wizard_views.xml',
        'wizard/mrp_quality_inspect_views.xml',
        'wizard/sh_mrp_qc_wizard_views.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}
