{
    "name": "Custom Addons",
    "summary": "Addonstest",
    "author": "Ridho",
    "depends": [
        'hr', 'after_sales_service'
    ],
    "data": [
        # "security/ir.model.access.csv",
        "views/hr_employee.xml",
        "views/res_partner.xml",
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
    "uninstall_hook": "_uninstall_reset_changes",
}
