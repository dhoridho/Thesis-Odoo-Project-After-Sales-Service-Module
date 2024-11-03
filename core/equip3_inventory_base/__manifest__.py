{
    "name": "Equip3 - Inventory Base",
    "author": "Hashmicro / Rajib",
    "version": '1.3.22',
    "summary": """
    1. Cost per Warehouse
    2. Cost per Lot/Serial Numbers
    3. Inventory Adjustment with Cost
    """,
    "category": "Inventory/Inventory",
    "depends": [
        "stock_account",
        "equip3_general_features"
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "security/security.xml",
        "views/res_config_settings_views.xml",
        "views/product_views.xml",
        "views/stock_valuation_layer_views.xml",
        "views/stock_inventory_views.xml",
        "views/stock_quant_views.xml",
        "views/stock_inventory_log_views.xml",
        "wizard/stock_valuation_layer_revaluation_views.xml"
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'uninstall_hook': 'uninstall_hook'
}