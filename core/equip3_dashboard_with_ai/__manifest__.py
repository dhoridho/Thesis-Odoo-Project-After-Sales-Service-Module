{
    'name': 'Dashboard AI',
    'version': '1.1.9',
    'author': 'Hashmicro',
    'depends': [
        'izi_dashboard',
        'izi_data',
        'equip3_hashmicro_ui',
        'equip3_general_features',
    ],
    'summary': """
        Feature:
        - Rebrand label with changes IZI to Hashmicro,

    """,
    'data': [
        'security/res_groups.xml',
        'views/menu.xml',
        'views/assets.xml',
        'views/company_view.xml',
        'views/lab_api_key_wizard.xml',
        'views/izi_analysis.xml',
        
        
    ],
    'qweb': [
        "static/src/xml/izi_config_dashboard.xml",
    ],
    'auto_install': False,
    'installable': True,
    'application': True
}