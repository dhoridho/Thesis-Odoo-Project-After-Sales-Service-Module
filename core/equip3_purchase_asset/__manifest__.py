{
    'name': 'Purchase Asset',
    'version': '1.1.34',
    'category': 'Purchase/Purchase',
    'summary': '''
            This module is to manage purchase assets.
        ''',
    'depends': [
        "equip3_purchase_other_operation",
        "equip3_purchase_other_operation_cont",
    ],
    'data': [
        "data/ir_sequence.xml",
        "security/ir.model.access.csv",
        "views/purchase_asset_views.xml",
        "views/purchase_order_views.xml",
        "views/menu.xml",
        'wizard/purchase_flow_asset_views.xml',
        'wizard/assets.xml',
    ],

    'qweb': [
        'static/xml/asset_configuration_flow.xml',
    ],

    'demo': [],
    'auto_install': False,
    'installable': True,
    'application': True
}


