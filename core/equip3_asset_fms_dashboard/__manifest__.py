
{
    'name': "Equip3 Asset Fms Dashboard",
    'version': '1.1.7',
    'category': 'Extra Tools',
    'summary': """Create Configurable Dashboards Easily""",
    'description': """Create Configurable Dashboard Dynamically to get the information that are relevant to your business, department, or a specific process or need, Dynamic Dashboard, Dashboard, Dashboard Odoo""",
    'author': 'Hashmicro / Chirag Chauhan',
    'website': "https://www.Hashmicro.com",
    'company': 'Hashmicro / Chirag Chauhan',
    'maintainer': 'Hashmicro / Chirag Chauhan',
    'depends': ['base', 'maintenance', 'equip3_asset_fms_masterdata', 'equip3_asset_fms_operation', 'equip3_asset_fms_report', 'ks_dashboard_ninja','equip3_hashmicro_ui','equip3_asset_fms_restructure_menu'],
    'data': [
        'data/assets_data.xml',
        'data/ks_dashboard_ninja.xml',
        'data/ks_fms_dashboard_ninja.xml',
        'views/menu_icon.xml'
    ],
   'license': "AGPL-3",
    'installable': True,
    'auto_install': False,
    'application': False,
}
