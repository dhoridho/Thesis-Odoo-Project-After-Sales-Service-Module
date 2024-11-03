
{
    'name': 'Equip3 for Hashlite',
    'version': '1.1.3',
    'author': 'Hashmicro',
    'description': 'This module will help hide unused menu',
    'depends': [
        'equip3_consignment_sales',
        'equip3_sale_team_commission',
        'equip3_sale_loyalty',
        'equip3_fmcg_sale',
    ],
    'data': [
        'security/security.xml',
        'views/menu_hide.xml',
        'views/field_and_tab_hide.xml',
        
    ],
    'installable': True,
    'application': True,
}
