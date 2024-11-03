# -*- coding: utf-8 -*-
{
    'name': "Equip3 Sale Loyalty",

    'summary': """
        Manage your Loyality Management in sale""",

    'description': """
        This module manages these features :
        1. Loyalty Product
        2. Loyalty Point
    """,

    'author': "Hashmicro",
    'category': 'Sale',
    'version': '1.1.22',

    # any module necessary for this one to work correctly
    'depends': [        
        'product', 
        'bi_loyalty_generic', 
        'equip3_sale_other_operation',
        'point_of_sale',
        'equip3_sale_promo_coupon',
        # 'pragmatic_odoo_delivery_boy',
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/product_category.xml',
        'data/product_demo.xml',
        'data/ir_rule.xml',
        # 'data/account_account_data.xml',
        'data/ir_sequence.xml',
        'data/ir_cron.xml',
        'data/expiry_voucher_template.xml',
        'views/sale_order_view.xml',
        'views/loyalty_view.xml',
        'security/rule.xml',
        'views/customer_target.xml',
        'views/customer_voucher.xml',
        'views/res_partner.xml',
        'views/account_move_view.xml',
        'views/res_config_settings_view.xml'
    ],
    # only loaded in demonstration mode
    'demo': [

    ],
}
