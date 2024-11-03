# -*- coding: utf-8 -*-
{
    'name': "Equip3 Construction Accounting Operation",

    'summary': """
        This module to manage all operation of accounting in construction""",

    'description': """
        This module manages these features :
        - Invoice 
        - Vendor Bill
        - Risalah AR
        - Risalah AP
    """,

    'author': "HashMicro",
    'website': "http://www.hashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Construction',
    'version': '1.2.18',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'utm', 'equip3_accounting_operation', 'equip3_construction_purchase_operation',
                'om_account_asset','equip3_accounting_masterdata', 'equip3_construction_masterdata','equip3_construction_sales_operation', 
                'equip3_construction_operation', 'equip3_construction_accessright_setting','equip3_accounting_pettycash', 
                'equip3_accounting_cash_advance','equip3_general_setting'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'views/construction_accounting_css_assets.xml',
        'report/progressive_claim_report.xml',
        'report/progressive_claim_report_view.xml',
        'data/progressive_sequence.xml',
        'data/journal_data.xml',
        'data/chart_of_account_data.xml',
        'data/progressive_claim_invoice_creation.xml',
        'data/mail_template.xml',
        'data/monthly_create_invoice_reminder.xml',
        'views/project_inherit_view.xml',
        'views/progressive_claim_view.xml',
        'views/create_claim_request_view.xml',
        'views/approval_matrix_claim_request_view.xml',
        'wizard/claim_request_rejected_reason_view.xml',
        'views/account_pdf_report.xml',
        'views/master_term_view.xml',
        'views/sale_order_inherit.xml',
        'views/purchase_order_inherit_view.xml',
        'views/account_move_invoice_view.xml',
        'views/work_order_inherit_view.xml',
        'wizard/claim_retention_confirmation_view.xml',
        'wizard/unpaid_conf_wiz_view.xml',
        'wizard/progressive_invoice_view.xml',
        'views/account_asset_view.xml',
        'views/cost_in_progress_view.xml',
        'wizard/cancel_claim_confirmation_view.xml',
        'wizard/complete_project_wizard_view.xml',
        'wizard/cancel_project_wizard_view.xml',
        'views/petty_cash_view.xml',
        'views/pettycash_voucher_view.xml',
        'wizard/account_pettycash_fund_change_wizards_inherit.xml',
        'wizard/cancel_contract_wizard_view.xml',
        'wizard/cancel_contract_subcon_wizard_view.xml',
        'wizard/complete_progress_confirmation_view.xml',
        'views/cash_advance_inherit_view.xml',
        'wizard/progressive_claim_report_wizard_view.xml',
        'wizard/change_custom_claim_view.xml',
        'wizard/cash_advance_over_budget_validation_wizard_view.xml',
        'wizard/petty_cash_over_budget_validation_wizard_view.xml',
    ],

}
