# -*- coding: utf-8 -*-
{
    'name': "Inventory Main Flow",
    'summary': "Inventory Main Flow",
    'author': "Inventory Team",
    'version': '1.1.5',
    'category': 'Inventory/Inventory',
    'depends': ['base','equip3_hashmicro_ui','equip3_inventory_reports', 'equip3_inventory_operation'],
    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'wizard/inventory_main_flow.xml',
        'wizard/inventory_flow_wizard.xml',
        'views/menu_views.xml',
    ],
    'qweb': [
        'static/xml/inventory_main_flow.xml',
    ],
    'installable': True,
    'application': False,
}
