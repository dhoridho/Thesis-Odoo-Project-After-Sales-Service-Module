
{
    'name': 'Purchase Rental',
    'version': '1.1.30',
    'category': 'Purchase/Purchase',
    'depends': [
        'purchase',
        'purchase_last_price_info',
        'purchase_request',
        'merge_picking',
        'equip3_purchase_other_operation',
        'equip3_purchase_other_operation_cont',
        'equip3_inventory_operation',
        'account'
    ],
    'data': [
        "data/ir_sequence.xml",
        "data/data_account.xml",
        "security/ir.model.access.csv",
        "views/product_template_views.xml",
        "views/purchase_order_views.xml",
        "views/purchase_rental_orders_views.xml",
        "views/stock_picking_views.xml",
        "views/menu.xml",
        "views/extend_rental_view.xml",
        "views/purchase_request_view.xml",
        "views/purchase_agreement_view.xml",
        "wizard/purchase_flow_rental_views.xml",
        "wizard/assets.xml",
    ],

    'qweb': [
        'static/xml/rental_configuration_flow.xml',
    ],

    'demo': [],
    'installable': True,
    'application': True
}
