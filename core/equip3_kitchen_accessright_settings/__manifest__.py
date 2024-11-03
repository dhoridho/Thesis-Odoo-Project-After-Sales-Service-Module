{
    'name': 'Equip3 - Kitchen Accessright Settings',
    'version': '1.1.17',
    'category': 'Central Kitchen',
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
        'views/res_config_settings_views.xml',
        'views/menuitems.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': '_activate_central_kitchen',
}