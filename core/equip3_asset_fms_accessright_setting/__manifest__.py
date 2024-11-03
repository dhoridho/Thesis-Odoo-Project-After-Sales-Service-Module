# -*- coding: utf-8 -*-
{
    'name': "Equip3 Asset FMS Accessright Setting",
    'summary': "Equip3 Asset FMS Accessright Setting",
    'description': "Equip3 Asset FMS Accessright Setting",
    'author': "HashMicro",
    'website': "https://www.hashmicro.com",
    'category': 'Uncategorized',
    'version': '1.1.5',
    'depends': ['base','maintenance', 'equip3_asset_fms_masterdata', 'equip3_asset_fms_operation'],
    'data': [
        'security/asset_fms_accessrights.xml',
        'security/ir.model.access.csv',
        'views/maintenance_equipment.xml',
        'views/maintenance_work_order.xml',
        'views/employee_asset_request.xml',
        'views/approval_matrix_employee_asset_request.xml',
        'views/menu_items.xml',
        'views/maintenance_repair_order.xml',
        'views/employee_asset_request.xml',
        'views/employee_asset_return.xml',
        'views/maintenance_request.xml',
        'views/maintenance_facilities_area.xml',
        'security/ir_rule.xml'
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}
