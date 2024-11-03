
{
    'name' : 'Equip3 Sale Other Operation ',
    'version' : '1.5.55',
    'author': "Hashmicro",
    'category' : 'Sales',
    'summary' : 'Manage Customer Credit Limit and Invoice Due Days',
    'description': """
    This module manages these features :
    1. Credit Limit and Invoice Due Days Request
    2. Credit Limit and Invoice Due Days Approval Matrix
    3. Over Limit and Invoice Overdue in Sale Order
    4. Over Limit and Invoice Overdue Approval Matrix
    """,
    'depends' : [
                'equip3_accounting_analytical',
                'equip3_sale_operation',
                'quotation_revision',
                'equip3_general_features',
                'equip3_general_setting'
                ],
    'data' :[
        'data/ir_sequence.xml',
        'data/credit_limit_mail.xml',
        'data/sale_order_email_template.xml',
        "data/customer_credit_limit_email_template.xml",
        "data/customer_credit_limit_wa_template.xml",
        "data/ir_rule.xml",
        'security/ir.model.access.csv',
        'security/res_groups.xml',
        'wizard/sale_customer_credit_views.xml',
        'wizard/customer_credit_invoice_overdue.xml',
        'wizard/limit_request_wizard.xml',
        'wizard/limit_approval_matrix_reject_views.xml',
        'views/res_partner_views.xml',
        'views/limit_request_view.xml',
        'views/sale_order_views.xml',
        'views/limit_approval_matrix_views.xml',
        'views/res_config_settings_views.xml',
        'views/customer_credit_limit_analysis.xml',
        'views/template_customer_credit_report.xml',
        'views/customer_product_template_views.xml',
        'views/product_template_views.xml',
        'views/account_analytic_account.xml',
        'reports/quotation_report.xml',
    ],
    'demo' :[],
    'installable' : True,
    'application' : True,
    'auto_install' : False
}
