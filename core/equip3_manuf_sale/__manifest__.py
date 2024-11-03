# -*- coding: utf-8 -*-

{
    "name": "Equip 3 - Manufacturing Sale",
    "version": "1.1.6",
    "category": "Manufacturing",
    "summary": "Manufacturing Sales",
    "description": """
    1. Sales to Manufacturing
    2. Sales to Manufacturing Notification
    """,
    "author": "HashMicro / Rajib",
    "website": "www.hashmicro.com",
    "depends": [
        "sale_mrp",
        "equip3_sale_operation",
        "equip3_manuf_operations_contd"
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/assets.xml",
        "views/res_config_settings_views.xml",
        "views/product_template_views.xml",
        "views/sale_order_views.xml",
        "views/mrp_notification_views.xml",
        "views/mrp_menuitems.xml",
        "templates/auto_mail_template.xml"
    ],
    "qweb": [
        "static/src/xml/order_line_bom.xml"
    ],
    "installable": True,
    "application": True,
    "auto_install": False
}
