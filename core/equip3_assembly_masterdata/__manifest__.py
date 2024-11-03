{
    'name': 'Equip3 - Assembly Master Data',
    'version': '1.1.4',
    'category': 'Assembly',
    'description': '',
    'author': 'HashMicro / Rajib',
    'website': 'www.hashmicro.com',
    'depends': [
        'equip3_assembly_accessright_settings',
        'equip3_manuf_masterdata'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/mrp_bom_views.xml',
        'views/menuitems.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}