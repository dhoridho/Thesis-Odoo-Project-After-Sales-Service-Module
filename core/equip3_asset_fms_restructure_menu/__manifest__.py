# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Equip3 FMS Restructure Menu',
    'version': '1.1.2',
    'author': 'Hashmicro / Diki',
    'website': "https://www.hashmicro.com",
    'category': 'FMS',
    'summary': """
    Add submenu in the FMS. Menus will be duplicated from Asset Control.
    """,
    'depends': ['base', 'maintenance','equip3_asset_flow',
                'hr_maintenance', 'equip3_general_setting',
                'equip3_asset_fms_masterdata','equip3_asset_fms_operation',
                'maintenance_plan',],
    'data': [
        'views/fms_menu.xml',
        'views/category_menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
