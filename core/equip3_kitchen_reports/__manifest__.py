{
    'name': 'Equip3 - Kitchen Reports',
    'version': '1.1.18',
    'category': 'Central Kitchen',
    'description': '',
    'author': 'HashMicro / Rajib',
    'website': 'www.hashmicro.com',
    'depends': [
        'equip3_kitchen_operations'
    ],
    'data': [
        'views/assets.xml',
        'views/kitchen_production_views.xml',
        'views/stock_move_views.xml',
        'views/kitchen_cost_details.xml',
        'views/menuitems.xml',
        'reports/kitchen_production_record_report.xml',
    ],
    'qweb': [
        'static/src/xml/kitchen_flow.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}
