# -*- coding: utf-8 -*-
{
    'name': "Equip3 Construction Sale Operation",

    'summary': """
        This module to manage all operation of crm and sales in construction""",

    'description': """
        This module manages these features :
        - CRM Leads
        - BOQ
        - Variable Estimation
        - Quotation
    """,

    'author': "Hashmicro",
    'website': "http://www.hashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Construction',
    'version': '2.2.25',

    # any module necessary for this one to work correctly
    'depends': ['equip3_construction_masterdata',
                'equip3_crm_operation', 'equip3_sale_operation',
                'bi_job_cost_estimate_customer',
                ],
    
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'report/sale_order_report_view.xml',
        'report/job_estimate_report.xml',
        'report/job_estimate_report_view_new.xml',
        'report/sale_order_report.xml',
        'data/mail_template_data.xml',
        'views/sales_opportunities_view.xml',
        'views/project_opportunity_view.xml',
        'views/job_estimates_view.xml',
        'views/approval_matrix_job_estimate_view.xml',
        'wizard/upload_job_estimate.xml',
        'views/menu_item_const.xml',
        'views/project_sale_view.xml',
        'views/sale_order_const_view.xml',
        'views/res_partner_const_view.xml',
        'data/job_sequence_data.xml',
        'data/sale_order_sequence.xml',
        'views/construction_sale_css_assets.xml',
        'views/job_estimates_css.xml',
        'views/approval_matrix_sale_order_view.xml',
        'wizard/approval_matrix_sale_reject_view.xml',
        'wizard/approval_matrix_job_reject_view.xml',
        'views/job_estimate_revision_view.xml',
        'views/sale_order_const_cust_limit_view.xml',
        'wizard/partner_credit_limit_sale_view.xml',
        'wizard/limit_approval_matrix_reject_views.xml',
        'views/res_setting_config_view.xml',
        'wizard/job_estimate_cancel_view.xml',
        'wizard/job_estimate_report_view.xml',
        'wizard/sale_order_report_wizard_view.xml',
        'wizard/change_to_variation_order_view.xml',
        'wizard/existing_quotation_main_view.xml',
        'views/const_contract_letter_view.xml',
        'data/contract_letter.xml',        
        'views/job_estimate_template_view.xml',
        'wizard/conf_not_use_retention_view.xml',
        'wizard/conf_not_use_dp_view.xml',  
        'wizard/contract_completion_validation_wizard_view.xml',
        'wizard/project_completion_delete_confirmation_view.xml',
        'views/project_internal_menu.xml',
    ],
}
