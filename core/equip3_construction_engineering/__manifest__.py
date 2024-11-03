# -*- coding: utf-8 -*-

{
    'name': 'Equip3 Construction Engineering',
    'version': '1.1.9',
    'category': 'Construction',
    'description':
        """
        equip3_construction_engineering

    """,
    'summary': 'equip3_construction_engineering',
    'author': 'Hashmicro',
    'website': 'http://www.hashmicro.com',
    'depends': ['equip3_construction_purchase_operation', 'equip3_construction_operation',
                'equip3_construction_reports',
                'equip3_manuf_operations_contd', 'equip3_manuf_subcontracting'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/job_estimate_cascade_wizard_view.xml',
        'wizard/existing_quotation_inherit_view.xml',
        'wizard/material_purchase_request_wizard_inherit_view.xml',
        'wizard/purchase_request_line_make_purchase_order_inherit_view.xml',
        'views/project_project.xml',
        'views/variable_view.xml',
        'views/job_estimate.xml',
        'views/sale_order_const.xml',
        'views/mrp_bom_view.xml',
        'views/project_task.xml',
        'views/cost_sheet.xml',
        'views/project_budget.xml',
        'views/project_opportunity.xml',
        'views/mrp_plan_view.xml',
        'views/mrp_production_view.xml',
        'views/mrp_workorder_view.xml',
        'views/mrp_consumption_view.xml',
        'views/material_request_view.xml',
        'views/purchase_request_view.xml',
        'views/purchase_order_view.xml',
        'views/weekly_report.xml'
        ],
    'installable': True,
    'application': False,
    'auto_install': False
}