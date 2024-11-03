# -*- coding: utf-8 -*-
{
    'name': "equip3_inventory_consignment",
    'author': "HashMicro",
    'website': "www.hashmicro.com",
    'version': '1.2.13',
    'summary': 'Manage consignments activities.',

    # any module necessary for this one to work correctly
    'depends': ['stock',
                'sale_management',
                'point_of_sale',
                'website',
                'payment',
                'sale',
                'odoo_consignment_process',
                'equip3_hashmicro_ui',
                'web_domain_field',
                'equip3_inventory_operation',
                ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/vendor_bill_consignment.xml',
        'views/sale_order_view.xml',
        'views/stock_production_lot.xml',
        'views/product_view.xml',
        'views/stock_picking.xml',
        'views/hide_menu_consignment.xml',
        'views/menu_consignment.xml',
        'report/marginal_report.xml',
        'views/menu_views.xml',
        'wizards/wizard_for_process_consignment_view.xml',
        'views/stock_quant.xml',
        'wizards/wizard_qty_purchase_requisition.xml',
        'views/stock_move_line.xml',
        'wizards/wizard_for_create_vendor_bill.xml',
        'wizards/wizard_for_transfer_back_consignment.xml',
        'views/consignment_agreement_new.xml',
        'views/stock_valuation_layer.xml',
        'views/product_category.xml',
        'security/ir_rule.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
