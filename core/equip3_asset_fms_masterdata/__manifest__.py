# -*- coding: utf-8 -*-
{
    'name': "Equip3 Asset Fms Masterdata",

    'summary': """
        a Modul for Masterdata""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.2.54',
    'application': True,

    # any module necessary for this one to work correctly
    'depends': ['base',  
                'base_setup',
                'base_geolocalize',
                'maintenance', 
                'maintenance_plan',
                'base_maintenance',
                'maintenance_stages_email_response',
                'website_maintenance_request',
                'print_maintenance_request',
                'mail',
                'equip3_inventory_masterdata',
                'hr_maintenance', 
		        'base_maintenance_config',
                'website_job_workorder_request',
                'equipment_print_pdf_image',
                'material_purchase_requisitions',
                'product',
                'om_account_asset',
                'equip3_accounting_asset'],

    # always loaded
    'data': [
        # 'views/security.xml',
        'security/ir.model.access.csv',
        'data/maintenance_stage.xml',
        'views/asset.xml',
        'views/maintenance_image.xml',
        'views/view.xml',
        'views/views.xml',
        'data/sequence.xml',
        'data/asset_qrcode_template.xml',
        'data/action_server.xml',
        # 'data/scheduler.xml',
        'views/asset_qrcode_config_views.xml',
        'views/maintenance_teams.xml',
        'views/maintenance_vehicle.xml',
        'views/maintenance_fuel_logs.xml',
        'views/account_asset_asset_view.xml',
        'views/maintenance_type.xml',
        'views/product_template.xml',
        'views/product_template_views.xml',
        'views/approval_matrix_mwo.xml',
        'views/approval_matrix_mro.xml',
        'views/approval_matrix_mp.xml',
        'views/approval_matrix_asset_transfer.xml',
        'views/paper_format.xml',
        # 'views/maintenance_equipment_asset_barcode.xml',
        'views/maintenance_equipment_qrcode.xml',
        'views/qrbarcode.xml',
        'views/maintanence_facilities_area_qrcode.xml',
        'views/all_asset_barcode_report.xml',
        'views/res_config_settings.xml',
        'security/ir_rule.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
