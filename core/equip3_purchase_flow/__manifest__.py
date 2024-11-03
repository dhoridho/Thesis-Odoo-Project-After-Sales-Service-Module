# -*- coding: utf-8 -*-
{
    'name': "equip3_purchase_flow",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Purchase/Purchase',
    'version': '1.1.3',

    # any module necessary for this one to work correctly
    'depends': ['equip3_purchase_report'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/purchase_flow_goods_views.xml',
        'wizard/purchase_flow_views.xml',
        'wizard/purchase_flow_service_views.xml',
        'wizard/assets.xml',
    ],

    'qweb': [
        'static/xml/purchase_configuration_flow.xml',
        'static/xml/service_configuration_flow.xml',
    ],

    'installable': True,
    'application': False,
}
