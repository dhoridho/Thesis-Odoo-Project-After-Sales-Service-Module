# -*- coding: utf-8 -*-
{
    'name': "equip3_purchase_vendor_portal",

    'summary': """
        Vendor Pricelist - Portal""",

    'description': """
        Vendor Pricelist - Portal
    """,

    'author': "Hashmicro / (Yusup Firmansyah, Prince)",
    'website': "https://www.hashmicro.com/id/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Purchase/Purchase',
    'version': '1.2.26',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'website',
        'portal',
        'purchase',
        'sh_vendor_signup',
        'sh_rfq_portal',
        'equip3_purchase_other_operation',
        'equip3_purchase_operation',
        'sh_po_tender_portal',
        # 'pragmatic_odoo_delivery_boy'
    ],

    # always loaded
    'data': [
        "security/user_groups.xml",
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/vendor_pricelist_portal_template_view.xml',
        'views/purchase_portal_template_view.xml',
        'views/my_portal_template.xml',
        'views/rfq_tender_templates.xml',
        'views/rfq_open_tender_templates.xml',
        'views/open_tender_templates.xml',
        'views/assets.xml',
        'views/res_partner_views.xml',
        "views/tender_dashboard_views.xml",
        "views/portal_templates.xml",
        "views/blanket_order_portal_views.xml",
        "views/product_supplierinfo_view.xml",
        'views/portal_purchase_order_template.xml',
        'views/portal_purchase_tender_template.xml',
        "data/vendor_pricelist_menu.xml",
        "wizard/portal_wizard.xml",
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
