# -*- coding: utf-8 -*-
{
    'name': "equip3_asset_fms_report",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    "category": "Maintenance",
    'application': True,
    'version': '1.2.22',

    # any module necessary for this one to work correctly
    'depends': ['base', 'equip3_asset_fms_operation', 'general_template', 'web', 'equip3_hashmicro_ui'],
    
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/maintenance_equipment.xml',
        'report/report.xml',
        'report/template.xml',
        'report/maintenance_repair_report.xml',
        'report/maintenance_request_report.xml',
        'report/maintenance_wo_report.xml',
        'report/internal_asset_transfer.xml',
        'report/company_setting.xml',
        'report/asset_cost_report.xml',
        'report/vehicle_cost_report.xml',
        'report/maintenance_plan.xml',
        'report/maintenance_work_order_report.xml',
        'report/maintenance_repair_order_report.xml',
        'report/asset_cost_report_pivot.xml',
        'report/vehicle_cost_report_pivot.xml',
        'report/asset_budget.xml',
        'report/fuel_and_mileage_report.xml',
        'report/performance_reliability_report.xml',
        'report/maintenance_workorder_insight.xml',
        'report/maintenance_repairorder_insight.xml',
        'report/forecast_hour_meter_maintenance.xml',
        'report/forecast_hour_meter_maintenance_line.xml',
        'report/forecast_odo_meter_maintenance.xml',
        'report/maintenance_request_pivot.xml',
        # 'report/forecast_odo_meter_maintenance_line.xml',
        'views/asset_moves_view.xml',
        'security/ir_rule.xml',
    ],
}
