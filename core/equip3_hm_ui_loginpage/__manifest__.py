# -*- coding: utf-8 -*-
{
    'name': "equip3_hm_ui_loginpage",

    'summary': """
        Equip3 HM Login page - equip3_hm_ui_loginpage Modifer for Login Page""",

    'description': """
        Equip3 HM Login page - equip3_hm_ui_loginpage is mainly for modifing the login page design
    """,

    'website': "https://www.hashmicro.com/id/",

    'category': "Website",
    'version': '1.0.2',

    # any module necessary for this one to work correctly
    'depends': [
        'website','sh_backmate_theme_adv',
    ],

    # always loaded
    'data': [
        'views/home_page_view.xml',
        'views/assets.xml',
    ],
    'qweb': [

    ],
   'auto_install': True,
    # only loaded in demonstration mode
}