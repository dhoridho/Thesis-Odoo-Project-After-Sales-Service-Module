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
    'name': 'App Search By Date (Datetime) or Number Range，快速日期数字范围搜索',
    'version': '1.1.8',
    'author': 'Sunpop.cn',
    'category': 'web',
    'website': 'https://www.sunpop.cn',
    'license': 'LGPL-3',
    'sequence': 2,
    'summary': """
    Keyword: 
    quick search date range, search number range, filter date range, filter number range. date search. date range search. datetime search. number search.
    Search by date or number range in List, Kanban, Pivot, Graph View.
    """,
    'description': """
    1.List all the date/datetime field to select range.
    2.List all the integer/float/Monetary field to select range.
    3.Support List, Kanban, Pivot, Graph View.
    4.Auto get user timezone, global Timezone supported.
    5.Easy admin to enable/disable the search.
    6.Hide in mobile view, Show only when width > 992px

    1.可快速选择所有日期、日期时间类型字段进行范围搜索.
    2.可快速选择所有数值、金额类型字段进行范围搜索.
    3.支持列表，看板，透视，统计图表等多种视图.
    4.内置全球多时区支持.
    5.可单独设置是否打开日期，数据型的范围搜索.
    6.移动端隐藏，只有 width > 992px 时才显示

--------------------------------------------------

    """,
    'images': ['static/description/banner.png'],
    'depends': ['web'],
    'data': [
        'views/template_view.xml',
        # data
        'data/ir_config_parameter.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    "price": 68.00,
    "currency": "EUR",

    'installable': True,
    'application': True,
    'auto_install': True,
}
