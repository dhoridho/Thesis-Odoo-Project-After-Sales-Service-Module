# -*- coding: utf-8 -*-
#################################################################################
# Copyright(c): 2023-24
# All Rights Reserved.
#
# This module is copyright property of the author mentioned above.
# You can't redistribute/reshare/recreate it for any purpose.
#
#################################################################################

{
    'name': 'Simplify Access Management',
    'version': '14.0.12.6.14',
    'sequence': 5,
    'author': 'Hashmicro',
    'category': 'Services',
    'summary': """All In One Access Management App for setting the correct access rights for fields, models, menus, views for any module and for any user.""",

    'description': """
        All In One Access Management App for setting the correct access rights for fields, models, menus, views for any module and for any user.
        Configuring correct access rights in Hashmicro is quite technical for someone who has little experience with the system and can get messy if you are not sure what you are doing. This module helps you avoid all this complexity by providing you with a user friendly interface from where you can define access to specific objects.
	
    """,
    "images": ["static/description/banner.gif"],
    'data': [
        'security/ir.model.access.csv',
        'security/res_groups.xml',
        'data/view_data.xml',
        'views/access_management_view.xml',
        'views/assets.xml',
        'views/res_users_view.xml',
        'views/store_model_nodes_view.xml',
    ],
    # 'qweb': [
    #     'static/src/xml/base.xml',
    # ],
    'depends':['web','advanced_web_domain_widget','base'],
    'post_init_hook': 'post_install_action_dup_hook',
    'application': True,
    'installable': True,
    'auto_install': False,
    
}
