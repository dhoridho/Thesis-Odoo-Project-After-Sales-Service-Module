# -*- coding: utf-8 -*-
{
    'name': "Equip3 Consignment Portal",
    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",
    'description': """
        Long description of module's purpose
    """,
    'author': "Hashmicro",
    'category': 'Inventory/Inventory',
    'version': '1.1.2',
    'depends': [
        "web",
        "portal",
        "odoo_consignment_process"
    ],
    'data': [
        "views/assets.xml",
        "views/my_consignment_template.xml",
        "views/portal_templates.xml",
    ],  
    'installable': True,
}
