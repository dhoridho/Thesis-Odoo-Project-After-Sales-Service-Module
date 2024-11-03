# See LICENSE file for full copyright and licensing details.

{
    "name": "Multi-DB Synchronization",
    "version": "1.1.17",
    "category": "Tools",
    "license": "AGPL-3",
    "summary": "Multi-DB Synchronization",
    "author": "OpenERP SA, Serpent Consulting Services Pvt. Ltd.",
    "website": "http://www.serpentcs.com",
    "maintainer": "Serpent Consulting Services Pvt. Ltd.",
    "images": ["static/description/Synchro.png"],
    "depends": ["base", "account", "purchase_request", "equip3_pos_masterdata", "equip3_accounting_deposit", "equip3_purchase_operation", "hr_expense"],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "wizard/base_synchro_view.xml",
        "views/base_synchro_view.xml",
        "views/res_request_view.xml",
        "views/server_action.xml",
        "views/purchase_order_view.xml",
        "data/ir_cron.xml",
    ],
    "installable": True,
}
