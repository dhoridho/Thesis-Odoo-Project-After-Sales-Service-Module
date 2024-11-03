{
    'name': "Equip3 Sale Custom Printout",
    'category': 'Sales',
    'version': '1.1.6',
    "author": "HashMicro",
    "depends": [
        "equip3_sale_other_operation",
        "equip3_sale_other_operation_cont"
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/sale_printout_editor_views.xml",
        "wizard/blanket_printout_editor_views.xml",
        'wizard/blanket_order_report_wizard_views.xml',
        "wizard/sale_order_report_wizard_views.xml",
        "report/sale_report_views.xml",
        "report/blanket_report_views.xml",
        "report/sale_exclusive_report_views.xml",
        "report/blanket_exclusive_report_views.xml",
        "views/assets.xml",
        "views/sale_order_templates_views.xml",
        "views/blanket_order_templates_views.xml",
        "views/blanket_assets.xml",
        "views/blanket_order_templates_views.xml",
    ],
    "installable": True,
}
