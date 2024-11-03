# -*- coding: utf-8 -*-

# Created on 2019-01-04
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

{
    'name': "Stock Location Kanban, 库存位置看板",
    'version': '14.21.06.20',
    'summary': """
    Quick access to current stock product, recent move in, move out.
    stock kanban view. group by location type, Corridor (X),Shelves (Y),Height (Z).
    """,
    'description': """
    Stock Location Kanban.
    1. Add kanban view for stock location.
    增加库位看板视图。
    2. Quick access to current stock product stock dashboard.
    在库存面板中快速查看相关出入库明细。
    3. Quick access stock move in stock location.
    增加按库位统计面板，直接查看指定库位的当前库存产品、相关的出入库明细、相关的出入库统计。
    4. Add location group by type,Corridor (X),Shelves (Y),Height (Z)
    增加库位分组，按类型，通道，货架，高度。
    """,
    'author': 'Sunpop.cn',
    'website': 'https://www.sunpop.cn',
    'license': 'LGPL-3',
    'category': 'Warehouse',
    'sequence': 0,
    'price': 18.00,
    'currency': 'EUR',
    'depends': ['stock'],
    'data': [
        'views/stock_location_views.xml',
        'views/stock_picking_views.xml',
        'views/menus.xml',
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
    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
