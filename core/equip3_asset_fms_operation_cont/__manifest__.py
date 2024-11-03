{
    "name": "equip3_asset_fms_operation_cont",
    "summary": """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",
    "author": "HashMicro",
    "category": "Uncategorized",
    'version': '1.1.14',
    'application': True,
    "website": "http://www.hashmicro.com",
    "depends": ['base', 'equip3_inventory_operation', 'equip3_asset_fms_operation'],
    #loaded
    'data': [
        'security/ir.model.access.csv',
        'views/interwarehouse_transfer_asset.xml',
        'wizard/create_asset_wizard.xml'
    ],
}