{
    'name': 'Equip3 - Kitchen Master Data',
    'version': '1.1.12',
    'category': 'Central Kitchen',
    'description': '',
    'author': 'HashMicro / Rajib',
    'website': 'www.hashmicro.com',
    'depends': [
        'equip3_kitchen_accessright_settings', 
        'equip3_manuf_masterdata'
    ],
    'data': [
        'data/on_upgrade.xml',
        'security/ir.model.access.csv',
        'views/mrp_bom_views.xml',
        'views/menuitems.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}