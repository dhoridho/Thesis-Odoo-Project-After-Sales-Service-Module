{
    "name": "Sale Order Modifier",
    "summary": "Sale Mod",
    "version": "14.0.1.0.1", 
    "author": "Ridho",
    "depends": [
        'sale',
    ],
    "data": [
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
    "uninstall_hook": "_uninstall_reset_changes",
}
