{
    'name': 'Purchase Promo Coupon',
    'version': '1.1.7',
    'category': 'Purchase/Purchase',
    'summary': '''
            This module help you to use Vendor Promotion.
        ''',
    'depends': [
        "equip3_purchase_other_operation",
        "sale_coupon",
    ],
    'data': [
        "views/coupon_program_views.xml",
        "views/purchase_order_views.xml",
    ],
    'demo': [],
    'auto_install': False,
    'installable': True,
    'application': True
}