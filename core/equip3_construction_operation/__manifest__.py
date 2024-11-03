# -*- coding: utf-8 -*-
{
    'name': "Equip3 Construction Operation",

    'summary': """
        This module to manage actual vs budget, and all operation of construction management""",

    'description': """
        This module manages these features :
        - Cost Sheet
        - Work Order
        - Project Masterdata
    """,

    'author': "Hashmicro",
    'website': "http://www.hashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Construction',
    'version': '1.2.43',

    # any module necessary for this one to work correctly
    'depends': ['equip3_construction_sales_operation',
                'equip3_construction_masterdata', 'purchase', 'ks_sales_forecast',
                'equip3_inventory_control', 'hr_timesheet',
                'equip3_asset_fms_masterdata', 'equip3_asset_fms_operation', 'pad_project',
                ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'data/mail_template.xml',
        'data/asset_allocation_sequence.xml',
        'views/assets.xml',
        'views/project_note.xml',
        'views/project_issue.xml',
        'views/project_external.xml',
        'views/construction_management_css_assets.xml',
        'wizard/task_complete_confirm_wiz_view.xml',
        'wizard/product_usage_wiz_view.xml',
        'wizard/in_progress_confirm_wizard_view.xml',
        'wizard/force_start_project_task_wizard_view.xml',
        'views/project_budget_view.xml',
        'views/job_cost_sheet_view.xml',
        'views/job_estimate_view.xml',
        'views/sale_operation_inherit_view.xml',
        'data/cost_sheet_sequence.xml',
        'views/approval_matrix_cost_sheet_view.xml',
        'views/job_cost_sheet_css.xml',
        'views/project_task_view.xml',
        'views/approval_matrix_progress_history_view.xml',
        'views/progress_history_view.xml',
        'wizard/progress_rejected_reason_view.xml',
        'data/task_sequence.xml',
        'data/issue_stage_data.xml',
        'wizard/subtask_wiz_view.xml',
        'data/internal_transfer_budget_sequence.xml',
        'views/Internal_transfer_budget_view.xml',
        'views/internal_transfer_budget_approval_matrix_line_view.xml',
        'views/stock_scrap_request_inherit_view.xml',
        'views/approval_matrix_project_budget.xml',
        'views/approval_matrix_internal_transfer_budget_view.xml',
        'views/approval_matrix_budget_carry_over_view.xml',
        'views/approval_matrix_asset_allocation_view.xml',
        'views/variable_estimate_view.xml',
        'views/project_view.xml',
        'views/s_curve_view.xml',
        'views/predecessor_successor_view.xml',
        'views/project_issue_view.xml',
        'data/issue_sequence.xml',
        'views/project_template_view.xml',
        'views/job_order_template_view.xml',
        'views/asset_allocation_view.xml',
        'views/issue_stage_view.xml',
        'views/group_of_product_view_inherit.xml',
        'wizard/cost_sheet_approval_wizard_view.xml',
        'wizard/project_template_confirmation_wizard_view.xml',
        'wizard/project_task_completion_wizard_view.xml',
        'wizard/finish_to_finish_task_validation_wizard_view.xml',
        'wizard/completion_issue_wizard_view.xml',
        'wizard/inprogress_issue_wizard_view.xml',
        'wizard/solved_date_issue.xml',
        'wizard/approval_matrix_reject_view.xml',
        'wizard/wizard_budget_carry_over_view.xml',
        'wizard/wizard_material_estimation_view.xml',
        'wizard/wizard_labour_estimation_view.xml',
        'wizard/wizard_internal_asset_estimation.xml',
        'wizard/wizard_overhead_estimation_view.xml',
        'wizard/wizard_subcon_estimation_view.xml',
        'wizard/wizard_equipment_lease_estimation_view.xml',
        'wizard/progress_history_deletion_wizard_view.xml',
        'wizard/progress_history_approval_wizard_view.xml',
        'wizard/request_change_period_view.xml',
        'wizard/labour_usage_confirmation_wizard_view.xml',
        'wizard/existing_quotation_main_view.xml',
        'wizard/sale_order_report_wizard_view.xml',
        'wizard/job_estimate_report_view.xml',

        'data/budget_carry_over_sequence.xml',
        'views/material_estimation_view.xml',
        'views/labour_estimation_view.xml',
        'views/equipment_lease_estimation_view.xml',
        'views/internal_asset_estimation.xml',
        'views/subcon_estimation_view.xml',
        'views/overhead_estimation_view.xml',
        'views/budget_carry_over_view.xml',

        'wizard/cost_sheet_validation_wizard_view.xml',
        'wizard/internal_transfer_budget_over_budget_validation_view.xml',

        'views/project_internal_menu.xml',
        'data/ir_cron.xml',
        'data/ir_cron_gop.xml',

    ],

    'qweb': [
        'static/src/xml/tree_button.xml',
    ],
}
