# -*- coding: utf-8 -*-

{
    "name": "Equip 3 - Manufacturing Double Book Keeping",
    "version": "1.1.1",
    "category": "Manufacturing",
    "summary": "Manufacturing Double Book Keeping",
    "description": """
    Manufacturing Double Book Keeping
    """,
    "author": "HashMicro / Rajib",
    "website": "www.hashmicro.com",
    "depends": [
        "base_synchro",
        "equip3_manuf_inventory"
    ],
    "data": [
        'data/on_upgrade.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/server_action.xml',
        'views/base_synchro_obj_views.xml'
    ],
    "qweb": [
    ],
    "installable": True,
    "application": False,
    "auto_install": False
}
