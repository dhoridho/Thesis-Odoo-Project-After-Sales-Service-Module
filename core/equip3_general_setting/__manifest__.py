{
    'name': 'General Setting',
    'version': '1.3.10',
    'author': 'Hashmicro / Prince / Rajib',
    'category' : '',
    'depends': ['base_setup','mail','branch','base_geolocalize'],
    'data': [
        'security/ir_rule.xml',
        'data/ir_config_parameter.xml',
        'data/check_multi_company.xml',
        'view/assets.xml',
        'view/equip3_general_setting.xml',
        'view/menu.xml',
        'view/res_users_views.xml',
        'view/res_company_views.xml',
    ],
    'qweb': [
        "static/src/xml/switch_branch_menu.xml",
    ],
    'demo': [],
    'auto_install': False,
    'installable': True,
    'application': True,
    'post_load': '_monkey'
}