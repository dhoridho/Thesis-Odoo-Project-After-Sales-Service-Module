# -*- coding: utf-8 -*-
{
    'name': "awesome_theme_pro",

    'summary': """Awesome backend theme for community, multi tab theme, enterprise theme, modern theme""",

    'description': """
        awesome theme, this is none tab version of awesome theme
        multi tab
        awesome odoo
        animation theme
        multi style theme
        multi tab theme
        theme
        backend theme
        backend theme
        popup form
        mordern theme
        beauty theme
        nice theme
    """,

    'author': "awesome odoo",
    'website': "http://blog.anitahashmicro.com/",
    'live_test_url': "http://themepro.anitahashmicro.com",

    "category": "Themes/Backend",
    'version': '1.1.1',
    'license': 'OPL-1',
    'images': ['static/description/banner.png',
               'static/description/awesome_screenshot.gif'],
    
    'depends': ['base', 'web'],

    "application": False,
    "installable": True,
    "auto_install": False,

    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/assets.xml',

        'views/awesome_login_style1.xml',
        'views/awesome_login_style2.xml',
        'views/awesome_login_style3.xml',

        'views/awesome_web.xml',
        'views/awesome_pwa.xml',
        'views/awesome_theme_mode.xml',
        'views/awesome_theme_style.xml',
        'views/awesome_theme_style_item_group.xml',
        'views/awesome_theme_style_item_sub_group.xml',
        'views/awesome_theme_style_item.xml',
        'views/awesome_user_setting.xml',
        'views/awesome_company_view.xml',
        'views/awesome_res_user_view.xml',
        "views/awesome_theme_theme_var.xml",
        "wizard/awesome_import_theme_style.xml",
        "wizard/awesome_theme_mode_wizard.xml"
    ],

    'qweb': [
        'static/xml/*.xml',
    ],

    'price': 139
}
