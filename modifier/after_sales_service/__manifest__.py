{
    "name": "After Sales Management",
    "summary": "Manage After Sales Services",
    "version": "14.0.1.0.1",
    "author": "Ridho",
    'icon': '/after_sales_service/static/description/icon.png',
    "depends": [
        'sale'
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/after_sales_views.xml",
        "views/service_request_views.xml",
        "views/warranty_claim_view.xml",
        "views/repair_history_views.xml",
        # "views/customer_management_view.xml",
        # "views/notification_management.xml",
        # "views/technician_management_view.xml",
        'controller/warranty_claim_controller.xml',
        'controller/service_request_controller.xml',
        'static/src/views/assets.xml'
    ],
    'assets': {
        'web.assets_frontend': [
            'after_sales_service/static/src/js/warranty_claim.js',
            'after_sales_service/static/src/js/service_request.js',
        ],
    },
    "application": True,
    "installable": True,
    "auto_install": False,

}
