
{
    'name': 'Generate Asset',
    'version': '1.1.13',
    'author': 'Hashmicro',
    'depends': [
        'equip3_accounting_operation',
        'equip3_asset_fms_masterdata',
        'equip3_asset_fms_operation_cont',
        'stock',
    ],
    'data': [
        "security/ir.model.access.csv",
        "wizard/generate_asset_wizard.xml",
        'wizard/create_asset_wizard.xml',
        'views/rental_product_view.xml',
        'views/account_asset_asset.xml',
        'views/maintenance_view.xml'
    ],
    'installable': True,
    'application': True,
}
