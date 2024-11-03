# -*- coding: utf-8 -*-
{
    'name': "Equip3 Construction Masterdata",

    'summary': """
        Manage your Master Data""",

    'description': """
        Manage your Master Data
    """,

    'author': "Hashmicro",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Construction',
    'version': '1.2.16',

    # any module necessary for this one to work correctly
    'depends': ['abs_construction_management',
                'equip3_accounting_analytical', 'ks_gantt_view_base', 'equip3_inventory_masterdata',
                'equip3_purchase_masterdata', 'equip3_construction_accessright_setting',
                'equip3_asset_fms_masterdata',],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'security/project_security.xml',

        'data/sequence.xml',
        'data/retention_term_data.xml',

        'views/menu_icon.xml',
        'views/product_template_view.xml',
        'views/warehouse_view.xml',
        'views/section_view.xml',
        'views/project_view.xml',
        'views/res_partner_view.xml',
        'views/variable_view.xml',
        'views/product_category_views.xml',
        'views/purchase_action_view.xml',
        'views/line_assets.xml',
        'views/inherited_res_users.xml',
        'views/group_of_product_view.xml',
        'views/budget_period_view.xml',
        'views/penalty_view.xml',
        'views/asset_and_vehicle_views.xml',
        'views/menu_item.xml',
        'views/project_internal_menu.xml',
        'views/retention_terms_view.xml',
        'views/project_stage_view.xml',
        'views/project_task_view.xml',
        'views/project_scope_view.xml',
        'views/project_location.xml',

        'wizard/group_of_product_message.xml',
        'wizard/group_of_product_wizard_view.xml',
        'wizard/responsible_project_cancel.xml',
        'wizard/upload_variable_view.xml',
    ],
    # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
}
