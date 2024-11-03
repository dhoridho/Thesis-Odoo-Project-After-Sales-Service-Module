{
    'name': 'Equip3 - Assembly Accessright Settings',
    'version': '1.1.1',
    'category': 'Assembly',
    'description': '',
    'author': 'HashMicro / Rajib',
    'website': 'www.hashmicro.com',
    'depends': [
        'mrp',
        'equip3_hashmicro_ui',
        'equip3_general_setting'
    ],
    'data': [
        'security/security.xml',
        'views/menuitems.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': '_activate_assembly',
}