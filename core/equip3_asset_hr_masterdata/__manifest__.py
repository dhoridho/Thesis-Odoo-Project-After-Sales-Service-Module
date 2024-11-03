# -*- coding: utf-8 -*-
{
    'name': "equip3_asset_hr_masterdata",
    'summary': "equip3_asset_hr_masterdata",
    'description': "equip3_asset_hr_masterdata",
    'author': "PT. Hashmicro Solusi Indonesia",
    'website': "https://www.hashmicro.com",
    'category': 'Maintenance',
    'version': '0.1',
    'depends': [
                'base',
                'maintenance',
                'hr_maintenance',
                'equip3_asset_fms_masterdata',
                'equip3_asset_fms_operation'
                ],
    'data': [
        # 'security/ir.model.access.csv',
        'views/asset_category.xml',
        'views/maintenance_equipment.xml',
        'views/maintenance_work_order.xml',
        'views/maintenance_repair_order.xml',
    ],
}
