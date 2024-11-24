{
    "name": "Service Modifier",
    "summary": "Service Mod",
    "version": "14.0.1.0.1", 
    "author": "Ridho",
    "depends": [
        'sale',
    ],
    "data": [
        "security/ir.model.access.csv",
        "reports/email_service.xml",
        "views/service_view.xml",
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
    "uninstall_hook": "_uninstall_reset_changes",
}
