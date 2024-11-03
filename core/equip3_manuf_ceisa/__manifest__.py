# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Equip3 Manufacturing CEISA",
    "summary": """
        Integrations to Dirjen Beacukai with CEISA4.0 system""",
    "version": "1.1.2",
    "author": "Hashmicro",
    "website": "https://hashmicro.co.id",
    "depends": ["web", "bus", "base", "equip3_manuf_it_inventory"],
    "data": [
        'security/ir.model.access.csv',
        'data/ir_config_parameter.xml',
        'wizard/user_wizard_login.xml',
        ###'wizard/pop_message.xml',
        ###'views/res_company_views.xml',
        'views/res_config_setting_views.xml',
        'views/export_documents_view.xml',
        'views/import_documents_view.xml',
        'views/documents_bc23_view.xml',
        'views/documents_bc25_view.xml',
        'views/documents_bc27_view.xml',
        'views/documents_bc40_view.xml',
        'views/documents_bc41_view.xml',
        'views/documents_bc261_view.xml',
        'views/documents_bc262_view.xml',
        ],
    "demo": [],
    "installable": True,
}
