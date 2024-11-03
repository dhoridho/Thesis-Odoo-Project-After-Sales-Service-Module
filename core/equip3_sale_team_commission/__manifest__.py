# -*- coding: utf-8 -*-
{
    'name': "Equip3 Sale Team and and Commission",

    'summary': """
        Manage sales teams and sales commission""",

    'description': """
        This module manages these features :
        1. Sale Team
        2. Sale Commission
        3. Sale Commission Payment
        4. Sale Commission Summary
    """,
    'author': "Hashmicro",
    'category': 'Sales',
    'version': '1.3.20',

    # any module necessary for this one to work correctly
    'depends': [
        'sale',
        'base',
        'sale_management', 
        'account', 
        'general_template',
        'sh_sales_commission_target',
        'crm',
        'equip3_sale_masterdata'
    ],
    'data' : [
        'data/ir_sequence_data.xml',
        'data/ir_rule.xml',
        'security/ir.model.access.csv',
        'wizards/sale_commission_report_views.xml',
        'wizards/sale_summary_commission_report_view.xml',
        'wizards/sale_commission_excel_report_view.xml',
        'views/sale_team.xml',
        'views/sale_view.xml',
        'views/target_commision_view.xml',
        'report/sale_commission_report_template.xml',
        'report/sale_summary_commission_report_template.xml',
    ],
    "auto_install": True,
}