# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip 3 - Field Accessright',
    'author': 'Hashmicro',
    'version': '1.1.5',
    'summary': 'Equip 3 - Field Accessright',
    'description': '''Field Accessright implementation''',
    'author': 'HashMicro / Rajib',
    'website': 'www.hashmicro.com',
    'depends': [
        'base',
        'web'
    ],
    'data': [
        'views/res_groups_views.xml',
        'views/ir_model_views.xml'
    ],
    'qweb': [
    ],
    'post_load': '_patch',
    'uninstall_hook': '_revert',
    'installable': True,
    'application': False,
    'auto_install': False
}
