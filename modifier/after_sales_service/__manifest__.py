{
    "name": "After Sales Management",
    "summary": "Manage After Sales Services",
    "version": "14.0.1.0.1",
    "author": "Ridho",
    'icon': '/after_sales_service/static/description/icon.png',
    "depends": [
        'sale', 'product', 'website',
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "data/cron.xml",
        "data/groups.xml",

        "views/service_dashboard_view.xml",
        "views/service_request_views.xml",
        "views/warranty_claim_view.xml",
        "views/repair_history_views.xml",
        "views/warranty_period_view.xml",
        "views/product_inherit_view.xml",
        'views/sale_order_inherit_view.xml',
        "views/customer_management_view.xml",
        "views/notification_management.xml",
        # "views/technician_management_view.xml",

        'views/website_layout.xml',
        'controller/warranty_claim_controller.xml',
        'controller/service_request_controller.xml',
        'static/src/views/assets.xml',
    ],
    'qweb': [
        'static/src/views/service_dashboard.xml',
        ],

    'assets': {
        'web.assets_frontend': [
            'after_sales_service/static/src/js/warranty_claim.js',
            'after_sales_service/static/src/js/service_request.js',
        ],

        'web.assets_backend': [
            'after_sales_service/static/src/css/styles.css',
            'after_sales_service/static/src/css/dashboard.scss',
        ],
    },
    "application": True,
    "installable": True,
    "auto_install": False,

}
