# -*- coding: utf-8 -*-
{
    'name': "Equip3 Construction Purchase Other Operation",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "HashMicro",
    'website': "http://www.hashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Construction',
    'version': '1.1.24',

    # any module necessary for this one to work correctly
    'depends': ['base', 
                'equip3_purchase_other_operation', 
                'equip3_construction_purchase_operation',
                'equip3_construction_accessright_setting'],
                
    # always loaded
    'data': [
        'wizards/split_purchase_agreement.xml',
        'wizards/purchase_tender_create_wizard.xml',
        'security/ir.model.access.csv',
        'views/purchase_tender_view.xml',
        'views/variable_material_line_view.xml',
        'views/subcontracting_menu_view.xml',
        'views/split_material_subcon_tender_menu.xml',
        'views/purchase_tender_menu.xml',
        'views/agreement_tender_line_assets.xml',
        'views/purchase_request_view.xml',
        'views/approval_matrix_purchase_agreement.xml',
        'views/approval_matrix_blanket_order.xml',
        'report/purchase_order_report_view.xml',
        'report/purchase_order_report.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
