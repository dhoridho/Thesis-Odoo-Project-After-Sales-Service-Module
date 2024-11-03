# -*- coding: utf-8 -*-

# Created on 2019-01-04
# author: 广州尚鹏，https://www.sunpop.cn
# email: 300883@qq.com
# resource of Sunpop
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

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

{
    'name': "Number no negative Configurable, Show null when zero. cell mull equal to zero or Greater than zero",
    'version': '1.1.1',
    'author': 'Sunpop.cn',
    'category': 'Base',
    'website': 'https://www.sunpop.cn',
    'license': 'LGPL-3',
    'sequence': 2,
    'summary': """
    Configurable Number no negative. Easy apply to all list, one2may list.
    Show null when zero in list. widget number restrict Configurable.
    set negative_allow in xml to set whether allow <0. or set app_negative_allow in global config.
    """,
    'description': """    
    Support Odoo 14,13,12, Enterprise and Community Edition
    1. Configurable Number no negative.
    2. Apply for integer, float, money field
    3. Default apply for all number, easy config with global param 'app_negative_allow'
    4. Easy config for prefer view with option 'negative_allow'    
    5. Show null when zero with options options="{'nozero':1}", show nothing when zero 0
    11. Multi-language Support.
    12. Support Odoo 14，13, 12 Enterprise and Community Edition
    ==========
    1. 可配置全局参数，是否允许负数
    2. 对整数，浮点，金额类型均有效
    3. 默认对所有模型数字生效，可配置全局参数 app_negative_allow
    4. 可单独针对指定视图生效，参数 negative_allow
    5. list中当数据为0时不显示, options="{'nozero':1}"
    11. 多语言支持
    12. Odoo 14，13, 12, 企业版，社区版，多版本支持
    """,
    'price': 58.00,
    'currency': 'EUR',
    'depends': [
        'web',
    ],
    'images': ['static/description/banner.gif'],
    'data': [
        'data/ir_config_parameter.xml',
        'views/webclient_templates.xml',
    ],
    'demo': [
    ],
    'test': [
    ],
    'css': [
    ],
    'qweb': [
    ],
    'js': [
    ],
    'post_load': None,
    'post_init_hook': None,
    'installable': True,
    'application': True,
    'auto_install': True,
}
