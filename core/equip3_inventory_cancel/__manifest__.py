# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

{
    "name": "Cancel Stock Picking | Delete Stock Picking | Delete Stock Moves",
    "author": "Hashmicro",
    "website": "www.hashmicro.com",
    "category": "Warehouse",
    "summary": "Cancel Inventory Picking, Cancel stock moves",
    "description": """This module helps to cancel stock-picking, You can also cancel multiple stock-picking, stock moves from the tree view. You can cancel the stock-pickin in 3 ways,

1) Cancel Only: When you cancel the stock-picking then the stock-picking are cancelled and the state is changed to "cancelled".
2) Cancel and Reset to Draft: When you cancel the stock-picking, then sotck-picking are cancelled and then reset to the draft state.
3) Cancel and Delete: When you cancel the stock-picking are cancelled and then the stock-picking will be deleted.""",
    "version": "1.1.1",
    "depends": [
                "stock",
    ],
    "application": True,
    "data": [
        'security/stock_security.xml',
        'data/data.xml',
        'views/res_config_settings.xml',
        # 'views/views.xml',
    ],
    "images": ["static/description/icon.png", ],
    "auto_install": False,
    "installable": True,
}
