

{
    "name": "Equip 3 - Mining Dashboard",
    "version": "1.1.3",
    "category": "",
    "summary": "Equip 3 - Mining Dashboard",
    "description": """Equip 3 - Mining Dashboard""",
    "author": "HashMicro / Rajib",
    "website": "www.hashmicro.com",
    "depends": [
        "equip3_mining_reports",
        "equip3_open_weather",
        "equip3_date_year"
    ],
    "data": [
        "data/ir_config_data.xml",
        "views/assets.xml",
        "views/mining_site_control_views.xml",
        "views/res_config_settings_views.xml",
        "views/plan_task_check_list_views.xml",
        "views/iconmenu.xml"
    ],
    "qweb": [
        "static/src/xml/mining_site_dashboard.xml",
    ],
    "installable": True,
}
