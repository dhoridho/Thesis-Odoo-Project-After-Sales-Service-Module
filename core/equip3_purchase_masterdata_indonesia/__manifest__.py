# -*- coding: utf-8 -*-
{
    'name': "equip3_purchase_masterdata_indonesia",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Hasmicro",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Purchase',
    'version': '1.1.16',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'sh_vendor_signup',
        'equip3_purchase_masterdata',
        'equip3_purchase_vendor_portal',
        'equip3_accounting_masterdata',
        'l10n_id_efaktur'
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/assets_frontend.xml',
        'views/res_partner_views.xml',
        'views/purchase_agreement_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}