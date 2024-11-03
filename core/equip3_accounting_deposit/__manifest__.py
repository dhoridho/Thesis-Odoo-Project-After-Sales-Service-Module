
{
    'name': 'Accounting Deposit',
    'version': '1.2.34',
    'author': 'Hashmicro / Prince',
    'category' : 'Accounting',
    'depends': [
        'account',
        'analytic',
        'branch',
        'equip3_general_features',
        'equip3_accounting_operation',

    ],
    'data': [
       'data/ir_sequence_data.xml',
       'data/customer_deposit_template.xml',
       'data/vendor_deposit_template.xml',
       'data/customer_deposit_wa_template.xml',
       'data/customer_deposit_wa_template_data_variable.xml',
       'data/vendor_deposit_wa_template.xml',
       'data/vendor_deposit_wa_template_data_variable.xml',
       'security/ir.model.access.csv',
       'report/exclusive_report.xml',
       'report/customer_deposit_report.xml',
       'report/vendor_deposit_report.xml',
       'wizard/convert_to_revenue_view.xml',
       'wizard/return_deposit_wizard_view.xml',
       'wizard/reconcile_deposit_wizard_view.xml',
       "wizard/reconcile_vendor_deposit_wizard_view.xml",
       'wizard/customer_deposit_reject.xml',
       'wizard/vendor_deposit_wizard.xml',
       'views/customer_deposit_views.xml',
       'views/vendor_deposit_views.xml', 
       'wizard/add_cust_deposit_amount_wizard.xml',
       'wizard/add_vendor_deposit_amount_wizard.xml'
    ],
    'demo': [],
    'auto_install': False,
    'installable': True,
    'application': True
}
