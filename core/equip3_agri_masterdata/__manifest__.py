# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip 3 - Agriculture Materdata',
    'author': 'Hashmicro',
    'version': '1.1.10',
    'category': 'Agriculture',
    'summary': 'Equip 3 - Agriculture Masterdata',
    'description': '''''',
    'author': 'HashMicro / Rajib',
    'website': 'www.hashmicro.com',
    'depends': [
        'hr',
        'stock',
        'equip3_agri_accessright_settings'
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'data/crop_activity_category_data.xml',
        'data/crop_activity_type_data.xml',
        'data/crop_activity_harvest_type_data.xml',
        'views/assets.xml',
        'views/res_config_settings_views.xml',
        'views/product_views.xml',
        'views/crop_estate_views.xml',
        'views/agriculture_division_views.xml',
        'views/crop_block_views.xml',
        'views/agriculture_crop_views.xml',
        'views/crop_phase_views.xml',
        'views/crop_activity_group_views.xml',
        'views/crop_activity_views.xml',
        'views/agriculture_worker_group_views.xml',
        'views/hr_employee_views.xml',
        'views/menuitems.xml'
    ],
    'qweb': [
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}
