# -*- coding: utf-8 -*-
{
    'name': "Equip3 - Inventory Masterdata",

    'summary': """
        Manage your Inventory Master Data""",

    'description': """
        Manage your Inventory Master Data
    """,

    'author': "Hashmicro",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Inventory/Inventory',
    'version': '1.3.41',

    # any module necessary for this one to work correctly
    'depends': [
        'stock_account',
        'equip3_general_features',
        'equip3_inventory_accessright_setting',
        'app_stock_location_capacity',
        'sh_product_multi_barcode',
        'stock_3dview',
        'dynamic_product_bundle',
        'warehouse_stock_restrictions',
        'base',
        'product',        
        'product_email_template',
        'stock_dropshipping',
        'product_expiry_warning'
    ],

    # always loaded
    'data': [
        'data/account_account_data.xml',
        'data/on_upgrade.xml',
        # 'data/update_sequence_picking_type.xml',
        'security/ir.model.access.csv',
        'security/products.xml',
        # 'security/stock_location.xml',
        'security/stock_picking.xml',
        "wizard/product_template_create_variant_wizard.xml",
        'views/product.xml',
        'views/product_brand_inherit.xml',
        'views/material_approval_matrix_view.xml',
        "views/internal_transfer_approval_matrix_view.xml",
        'views/stock_inventory_approval_matrix_view.xml',
        'views/stock_scrap_approval_matrix_view.xml',
        'views/stock_location_views.xml',
        'views/product_template_new.xml',
        'views/stock_quant_package_views.xml',
        'data/create_op_type.xml',
        "views/assets.xml",
        "views/stock_warehouse_view.xml",
        "views/barcode_menu_views.xml",
        "views/barcode_label_report.xml",
        "views/product_attribute.xml",
        "views/stock_picking.xml",
        "wizard/barcode_labels.xml",
        "views/stock_putaway_rule_view.xml",
        "views/product_category_views.xml",
        "views/res_users_views.xml",
        "views/hide_menu.xml",
        "views/product_view.xml",
        "views/barcode_labels_views.xml",
        "views/res_partner.xml",
        "views/product_packaging_views.xml",
        "views/uom_inherit.xml",
        "views/stock_life.xml",
        "report/report_stock_forecasted.xml",
        "report/product_product_templates.xml",
        "wizard/pick_product_replenish_views.xml"
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    "qweb": [
        "static/src/xml/templates.xml",
        "static/src/xml/location_removal_priority.xml",
        "static/src/xml/stock_quant_package.xml",
        "static/src/xml/report_stock_forecasted.xml",
    ],
}
