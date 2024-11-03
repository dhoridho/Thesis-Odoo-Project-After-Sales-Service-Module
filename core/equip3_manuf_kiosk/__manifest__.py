# -*- coding: utf-8 -*-

{
    "name": "Equip 3  - Manufacturing Kiosk Mode",
    "version": "1.2.12",
    "category": "Manufacturing",
    "summary": "Manufacturing Kiosk Mode",
    "description": """
    i. Work Center Kanban
    ii. Work Order Kanban
    iii. Kiosk Mode
    """,
    "author": "HashMicro",
    "website": "www.hashmicro.com",
    "depends": [
        "equip3_manuf_operations_contd"
    ],
    "data": [
        "views/mrp_workcenter_view.xml",
        "views/mrp_workorder_views.xml",
        "views/kiosk_assets.xml",
        "views/mrp_consumption_views.xml",
        "views/hr_employee_views.xml",
        "views/res_config_settings_views.xml"
    ],
    "qweb": [
        "static/src/xml/kiosk_template.xml",
        "static/src/xml/mrp_kiosk.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
