{
    'name': 'Equip3 - Assembly Reports',
    'version': '1.1.3',
    'category': 'Assembly',
    'description': '',
    'author': 'HashMicro / Rajib',
    'website': 'www.hashmicro.com',
    'depends': [
        'equip3_assembly_operations'
    ],
    'data': [
        'views/assets.xml',
        'views/assembly_production_views.xml',
        'views/stock_move_views.xml',
        'views/menuitems.xml',
        'views/assembly_cost_details.xml',
        'reports/assembly_production_record_report.xml'
    ],
    'qweb': [
        'static/src/xml/assembly_flow.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}