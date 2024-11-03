{
    'name': 'Equip3 - Inventory Scale',
    'author': 'Hashmicro / Rajib',
    'version': '1.1.3',
    'summary': 'Stock Picking Product Scale.',
    'depends': [
        "stock",
    ],
    'category': 'Inventory/Inventory',
    'data': [
        'data/scale_url_data.xml',
        'views/assets.xml',
        'views/stock_picking_view.xml',
        'views/res_config_settings_views.xml'
    ],
    'qweb': [
        'static/src/xml/stock_scale.xml'
    ],
    'installable': True,
    'application': True,
}
