# -*- coding: utf-8 -*-
{
    'name': "Equip3 FMCG Sale",

    'summary': """
        Equip3 FMCG Sale""",

    'description': """
        Equip3 FMCG Sale :
          1. Bank Guarantee
    """,

    'author': "Yusuf Firmansyah / Hashmicro",
    'website': "http://www.hashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'FMCG',
    'version': '1.1.14',

    # any module necessary for this one to work correctly
    'depends': ['base','sale','sh_sale_credit_limit','equip3_sale_masterdata','equip3_sale_operation','equip3_sale_other_operation','equip3_inventory_masterdata','equip3_sale_loyalty','general_template'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'data/ir_sequence.xml',
        'data/product.xml',
        'data/ir_rule.xml',
        'data/mail_templates.xml',
        'views/claim_to_principle_template.xml',
        'views/res_partner.xml',
        'views/limit_request.xml',
        'views/res_config.xml',
        'views/summary_for_principal.xml',
        'views/customer_voucher_view.xml',
        'views/fmcg_reimbursement_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
