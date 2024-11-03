{
    'name': 'Equip3 - Assembly Operations',
    'version': '1.1.17',
    'category': 'Assembly',
    'description': '',
    'author': 'HashMicro / Rajib',
    'website': 'www.hashmicro.com',
    'depends': [
        'mail',
        'branch',
        'stock_account',
        'purchase_request',
        'general_template',
        'equip3_assembly_masterdata',
        'equip3_inventory_operation',
        'ks_list_view_manager'
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'data/ir_sequence_data.xml',
        'views/assets.xml',
        'views/safety_stock_views.xml',
        'views/assembly_production_views.xml',
        'views/product_template_views.xml',
        'views/product_product_views.xml',
        'views/purchase_request_views.xml',
        'views/mrp_bom_views.xml',
        'views/menuitems.xml'
    ],
    'qweb': [
        'static/src/xml/dashboard.xml',
        'static/src/xml/assembly_template.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}