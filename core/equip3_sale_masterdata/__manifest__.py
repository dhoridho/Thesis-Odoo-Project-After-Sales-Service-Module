# -*- coding: utf-8 -*-
{
    'name': "Equip3 Sale Master Data",

    'summary': """
        Manage your master data in sale""",

    'description': """
        This module manages these features :
        1. Customer
        2. Product
        3. Pricelist
        4. Pricelist Approval Matrix
    """,

    'author': "Hashmicro",
    'category': 'Sales',
    'version': '1.1.63',

    # any module necessary for this one to work correctly
    'depends': [
        'sale', 'equip3_general_features', 'product', 'sale_product_configurator', 'web', 'ss_whatsapp_connector', 'acrux_chat_sale', 'dynamic_product_bundle', 'contract_recurring_invoice_analytic', 'auditlog', 'account', 'sale_timesheet','setu_rfm_analysis', 'sh_sale_pricelist', 'stock', 'equip3_kanban_view'
    ],

    # always loaded
    'data': [
        'data/ir_sequence_data.xml',
        "data/customer_degree_trust_data.xml",
        "data/ir_rule.xml",
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/product_template_views.xml',
        'views/sale_order_views.xml',
        'views/res_partner_views.xml',
        'views/customer_degree_trust.xml',
        'views/product_pricelist_view.xml',
        'views/res_config_settings_views.xml',
        'wizard/sale_order_alternative_products.xml',
        'views/customer_view.xml',
        'views/sale_team.xml',
        'views/customer_category.xml',
        'views/product_views_inherit.xml',
        'views/stock_warehouse.xml',
        'views/product_pricelist_request_views.xml',
        'views/product_pricelist_approval_matrix_views.xml',
        'views/product_pricelist_approval_entry_views.xml',
        'wizard/product_pricelist_approval_matrix_reject_views.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
    
    ],
}