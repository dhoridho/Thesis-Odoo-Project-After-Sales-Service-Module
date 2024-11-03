# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip3 Sale Promo Coupon',
    'summary': """
        Manage your Sale Promotion and Coupon Programs""",
    'description': """
        This module manages these features :
        1. Promotion Programs
        2. Coupon Programs
    """,
    'author': "Hashmicro",
    'category': 'Sales / Rajib',
    'version': '1.1.29',
    'depends': ['sale_coupon', 'equip3_sale_operation', 'equip3_inventory_masterdata'],
    'data': [
        'security/ir_rule.xml',
        'data/product_category.xml',
        'data/on_upgrade.xml',
        'data/product_promotion.xml',
        'views/coupon_program_view.xml',
        'views/sale_order_views.xml',
        'wizards/sale_coupon_apply_code_views.xml'
    ],
    'installable': True,
}