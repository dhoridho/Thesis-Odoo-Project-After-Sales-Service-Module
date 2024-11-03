# -*- coding: utf-8 -*-
{
    'name': "equip3_consignment_sales",

    'summary': """
        Module Consignment Sales""",

    'description': """
        Manage Consignment Sales Process
    """,

    'author': "Hashmicro",
    'website': "http://www.hashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Sales',
    'version': '1.1.23',

    # any module necessary for this one to work correctly
    'depends': ['base','sale','equip3_sale_masterdata','equip3_sale_operation','equip3_sale_purchase','equip3_accounting_analytical'],

    # always loaded
    'data': [
        # 'security/security.xml',
        'security/ir.model.access.csv',
        # 'data/stock_data.xml',
        'data/asset.xml',
        'data/ir_cron.xml',
        'data/ir_sequence.xml',
        'views/consignment_quo_views.xml',
        'views/consignment_views.xml',
        'views/templates.xml',
        'views/partner_view.xml',
        'views/sale_consignment_agreement_view.xml',
        'views/res_config_settings_view.xml',
        'views/internal_transfer.xml',
        'views/sale_order_views.xml',
        'views/stock_picking_view.xml',
        'views/account_move_view.xml',
        'views/product_template_view.xml',
        'reports/consignment_stock_views.xml',
        'reports/consignment_analysis_views.xml',
    ],
}
