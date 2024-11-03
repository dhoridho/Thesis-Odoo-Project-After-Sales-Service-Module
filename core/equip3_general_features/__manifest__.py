# -*- coding: utf-8 -*-
{
    'name': "Equip3 - General Features",

    'summary': """
        Manage General Features include Company, Branch, and Product""",

    'description': """
        
    """,

    'author': "Hashmicro",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.1.42',

    # any module necessary for this one to work correctly
    'depends': ['sale_stock', 'base', 'product', 'branch', 'mail', 'ks_dashboard_ninja', 'kpi_scorecard', 'bi_view_editor', 'board', 'equip3_general_setting','delivery','sale_timesheet'],

    # always loaded
    'data': [
        'data/ir_config_parameter.xml',
        'data/ir_cron.xml',
        'data/data_connector.xml',
        'data/res_country_city_data.xml',
        'security/ir.model.access.csv',
        # 'views/views.xml',
        'views/templates.xml',
        'views/product_category_views.xml',
        'views/product_product_views.xml',
        'views/product.xml',
        'views/product_brand.xml',
        'views/res_company_views.xml',
        "views/res_config_settings_view.xml",
        'views/res_branch_views.xml',
        'views/res_users_views.xml',
        'views/res_country.xml',
        'views/res_country_state.xml',
        'views/res_city.xml',
        "views/access_rights_profile_view.xml",
        'views/record_creator_views.xml',
        'views/mydashboard_menu_views.xml',
        'views/qiscus_wa_template.xml',
        'views/wa_message_template.xml',
        'views/qiscus_wa_variable.xml',
        'views/wa_connector.xml',
        'wizard/whatsapp_test_template.xml',
        'wizard/create_template_qiscuss_wizard.xml'

    ],
    # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
     'qweb': [
        'static/src/xml/custom_button.xml'
     ]
     
}
