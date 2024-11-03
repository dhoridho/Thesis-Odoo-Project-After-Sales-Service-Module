# -*- encoding: utf-8 -*-

{
    "name": "Equip3 accounting SG",
    "version": "1.1.4",
    "author": "MasBin",
    'website': '',
    "category": "Accounting SG",
    "description": """
                
            """,
    #     "depends" : ["base","product","sale",'sale_enhancement','account_accountant'],
    # removed account_accountant module dependency, doesnt exist in odoo11
    "depends": ["base", "sg_account_reports_groupby", "sg_account_report","account"],
    "init_xml": [],
    "demo_xml": [

    ],
    "data": [
        "security/ir.model.access.csv",
        "data/data.xml",
        "views/hide_menu.xml",
        "views/form_c.xml",
        "views/form_cs.xml",
        "views/account_tax_views.xml",
        "report/form_cs_report.xml",
        # "data/hotel_folio_workflow.xml",
    ],
    "active": False,
    "installable": True,
    'application': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
