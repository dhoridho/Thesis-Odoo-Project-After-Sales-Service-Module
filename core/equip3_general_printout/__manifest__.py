
{
    'name': 'General Printout',
    'version': '1.1.3',
    'author': 'Hashmicro / Prince',
    'depends': [
        "general_template",
        "purchase",
        "web",
    ],
    'data': [
        "security/ir.model.access.csv",
        "data/purchase_order_template.xml",
        "report/purchase_report_views.xml",
        "report/purchase_exclusive_report_views.xml",
        "views/assets.xml",
        "views/purchase_order_template_views.xml",
        "views/purchase_order_views.xml",
        "wizard/printout_editor_views.xml",
        "wizard/print_purchase_report_views.xml",
    ],
    'installable': True,
    'application': True,
}
