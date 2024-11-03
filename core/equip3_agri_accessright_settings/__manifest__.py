# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip 3 - Agriculture Accessright Settings',
    'author': 'Hashmicro',
    'version': '1.1.6',
    'category': 'Agriculture',
    'summary': 'Equip 3 - Agriculture Accessright Settings',
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
        'views/agri_approval_matrix_views.xml',
        'views/agri_approval_matrix_entry_views.xml',
        'views/res_config_settings_views.xml',
        'views/agri_menuitems.xml',
        'views/menu_category.xml',
        'templates/mail_template_reuse.xml'
    ],
    'qweb': [
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}
