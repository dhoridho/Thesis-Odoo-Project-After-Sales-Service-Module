# -*- coding: utf-8 -*-
{
    'name': "Equip3 Construction Purchase Operation",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Muhammad Andi Laksamana",
    'website': "http://www.hashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Construction',
    'version': '1.2.31',

    # any module necessary for this one to work correctly
    'depends': [
                'equip3_purchase_other_operation',
                'equip3_purchase_other_operation_cont',
                'equip3_purchase_rental',
                'equip3_inventory_operation', 
                'equip3_construction_sales_operation', 
                'equip3_construction_operation',
                'equip3_construction_accessright_setting'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        # 'security/ir_rule.xml',
        'wizard/purchase_agreement_views.xml',
        'wizard/purchase_agreement_wiz_view.xml',
        'wizard/material_request_wiz_view.xml',
        'wizard/material_purchase_request_wizard.xml',
        'wizard/purchase_request_line_make_purchase_order.xml',
        'wizard/intra_interwarehouse_wizard.xml',
        'wizard/conf_not_use_dp_view.xml',
        'wizard/conf_not_use_retention_view.xml',
        'views/project_view.xml',
        'views/split_material_subcon_menu.xml',
        'views/material_request.xml',
        'views/material_request_approval_matrix_view.xml',
        'views/variable_estimate_view.xml',
        'views/purchase_request_view.xml',
        'views/intra_internal_transfer_views.xml',
        'views/rfq_view.xml',
        'views/line_assets.xml',
        # 'views/purchase_agreement_view.xml',
        'views/job_cost_sheet_view.xml',
        'views/approval_matrix_purchase_order.xml',
        'views/approval_matrix_purchase_request.xml',
        'views/variable_template_view.xml',
        'views/purchase_penalty_view.xml',
        'views/purchase_menu.xml',
        'views/project_task_view.xml',
        'views/purchase_requisition_view.xml',
        'wizard/purchase_order_over_budget_validation_wizard_view.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
