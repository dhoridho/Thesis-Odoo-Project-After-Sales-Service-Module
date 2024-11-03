# -*- coding: utf-8 -*-

# Created on 2018-11-26
# author: 广州尚鹏，https://www.sunpop.cn
# email: 300883@qq.com
# resource of Sunpop
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

# Odoo12在线用户手册（长期更新）
# https://www.sunpop.cn/documentation/user/12.0/en/index.html

# Odoo12在线开发者手册（长期更新）
# https://www.sunpop.cn/documentation/12.0/index.html

# Odoo10在线中文用户手册（长期更新）
# https://www.sunpop.cn/documentation/user/10.0/zh_CN/index.html

# Odoo10离线中文用户手册下载
# https://www.sunpop.cn/odoo10_user_manual_document_offline/
# Odoo10离线开发手册下载-含python教程，jquery参考，Jinja2模板，PostgresSQL参考（odoo开发必备）
# https://www.sunpop.cn/odoo10_developer_document_offline/
# description:

{
    'name': 'Boost Speed. Speed up clean core.',
    'version': '14.21.02.04',
    'author': 'Sunpop.cn',
    'category': 'Productivity',
    'website': 'https://www.sunpop.cn',
    'license': 'LGPL-3',
    'sequence': 2,
    'summary': """ 
    Clean erp with speed up.
    Stop auto subscribe. Stop mail. Stop follower. Stop Discuss.    
    Boost speed.Faster and quick develop. odoo boost. odoo speed up.
    """,
    'description': """   
    Boost Speed. speed up. Support Odoo 14,14.0
    1. Easy to switch. Disable / Enable all the follow function.
    2. Disable odoo Discuss.
    3. Disable odoo poll. Disable odoo polling. Speed up Especially in Windows Development.
    4. Disable subscribe. Disable odoo follow. Disable odoo followers
    5. Disable mail notify. Disable mail. Disable notify.
    6. Disable Auto cron Fetchmail Service.
    
    Disable all can make odoo more fast, Speed up Especially in Windows Development.
    ============
    odoo 提速
    1. 可设置 停用/启用用户自动订阅
    1. 可设置 停用/启用对话沟通
    2. 可设置 停用/启用系统消息总线
    停用后可极大提速 odoo，特别是在 windows 下，可以解决因长连接问题导致的不断 Connection lost。
    """,
    'images': ['static/description/banner.png'],
    'price': 68.00,
    'currency': 'EUR',
    'depends': [
        'bus',
        'payment',
        'im_livechat',
        'app_odoo_customize',
    ],
    'data': [
        'views/app_theme_config_settings_views.xml',
        'views/webclient_templates.xml',
        'data/res_groups.xml',
        'data/ir_ui_menu.xml',
        'data/ir_cron_data.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'demo': [],
    'test': [],
    'css': [],
    'js': [],
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
    'auto_install': True,
}
