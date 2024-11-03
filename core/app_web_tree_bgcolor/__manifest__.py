# -*- coding: utf-8 -*-

# Created on 2019-01-04
# author: 广州尚鹏，https://www.sunpop.cn
# email: 300883@qq.com
# resource of Sunpop
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

# Odoo12在线用户手册（长期更新）
# https://www.sunpop.cn/documentation/user/13.0/en/index.html

# Odoo12在线开发者手册（长期更新）
# https://www.sunpop.cn/documentation/13.0/index.html

# Odoo10在线中文用户手册（长期更新）
# https://www.sunpop.cn/documentation/user/10.0/zh_CN/index.html

# Odoo10离线中文用户手册下载
# https://www.sunpop.cn/odoo10_user_manual_document_offline/
# Odoo10离线开发手册下载-含python教程，jquery参考，Jinja2模板，PostgresSQL参考（odoo开发必备）
# https://www.sunpop.cn/odoo10_developer_document_offline/

# Copyright 2015 AvanzOSC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "List View Background Dynamic Color",
    'summary': 'Set background color in List View, Tree view, order track, sale order alert, purchase order alert',
    "version": "14.21.10.18",
    'category': 'Base',
    'author': 'Sunpop.cn',
    'website': 'https://www.sunpop.cn',
    'license': 'LGPL-3',
    'sequence': 2,
    'installable': True,
    'auto_install': True,
    'application': True,
    'images': ['static/description/banner.gif'],
    'currency': 'EUR',
    'price': 38,
    'description': """
        Dynamic background color widget, set Background Color in Tree view List view.
        Can use in sale, purchase, or andy data module.
        Good for date alert.
    """,
    'depends': [
        'app_common',
        # please uncommented the follow if you need to use in sale or purchase, it's a sample in sale order and purchase.
        # 'sale_management',
        # 'purchase',
    ],
    "data": [
        'views/templates.xml',
        # please uncommented the follow if you need to use in sale or purchase, it's a sample in sale order and purchase.
        # 'views/sale_order_views.xml',
        # 'views/purchase_order_views.xml',
    ],
}
