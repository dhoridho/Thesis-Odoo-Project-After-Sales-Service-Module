{
    "name": "Equip3 Asset Fms Tracking",
    "summary": """""",
    "author": "HashMicro",
    "category": "Uncategorized",
    'version': '1.1.8',
    'application': True,
    "website": "http://www.hashmicro.com",
    "depends": ['base', 'equip3_asset_fms_masterdata', 'base_setup','base_geolocalize',],
    #loaded
    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'wizard/maintenance_asset_tracking_views.xml',
        'data/ir_config_parameter_data.xml',
    ],
}