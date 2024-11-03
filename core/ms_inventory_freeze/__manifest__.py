{
    "name"          : "Inventory Freeze (Inventory Adjustment)",
    "version"       : "1.0",
    "author"        : "Miftahussalam",
    "website"       : "https://blog.miftahussalam.com",
    "category"      : "Inventory",
    "license"       : "LGPL-3",
    "support"       : "me@miftahussalam.com",
    "summary"       : "Can't move stock while inventory adjustment process",
    "description"   : """
        Inventory Freeze While Inventory Adjustment Process
    """,
    "depends"       : [
        "base",
        "product",
        "stock",
    ],
    "data"          : [
        "views/ms_inventory_freeze_view.xml",
    ],
    "demo"          : [],
    "test"          : [],
    "images"        : [
        "static/description/images/main_screenshot.png",
    ],
    "qweb"          : [],
    "css"           : [],
    "application"   : True,
    "installable"   : True,
    "auto_install"  : False,
}