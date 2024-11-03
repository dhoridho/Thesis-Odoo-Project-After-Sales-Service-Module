# -*- coding: utf-8 -*-
{
    'name': "equip3_sale_configuration_flow",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Hashmicro",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sales',
    'version': '1.1.7',

    # any module necessary for this one to work correctly
    'depends': ['equip3_sale_other_operation'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/sale_flow_wizard_views.xml',
        'wizard/assets.xml',
    ],

    'qweb': [
        'static/xml/sale_configuration_flow.xml'
    ],

    'installable': True,
    'application': False,
}
