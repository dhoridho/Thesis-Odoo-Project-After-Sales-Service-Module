# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip 3 - Mining Accessright Settings',
    'author': 'Hashmicro',
    'version': '1.1.4',
    'category': 'Mining',
    'summary': 'Equip 3 - Mining Accessright Settings',
    'description': '''''',
    'author': 'HashMicro / Rajib',
    'website': 'www.hashmicro.com',
    'depends': [
        'branch',
        'equip3_general_setting',
        'equip3_hashmicro_ui'
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/mining_approval_matrix_views.xml',
        'views/mining_approval_matrix_entry_views.xml',
        'views/res_config_settings_views.xml',
        'views/mining_menuitems.xml',
        'views/menu_category.xml',
        'templates/mail_template_reuse.xml'
    ],
    'qweb': [
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}
