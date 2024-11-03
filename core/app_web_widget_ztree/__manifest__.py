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
# change ztree to  https://github.com/wenzhixin/font-awesome-zTree

{
    'name': 'App zTree widget, Many2One Hierarchy Parent tree in m2o select',
    'version': '14.20.10.06',
    'author': 'Sunpop.cn',
    'category': 'Base',
    'website': 'https://www.sunpop.cn',
    'license': 'LGPL-3',
    'sequence': 2,
    'summary': """
    show parent tree, parent children node in m2o select field.
    Use for parent children tree list select navigator. 
    ztree widget.
    """,
    'description': """
    zTree widget.
    Advance search with real parent children tree, ListView or KanbanView ,
    eg: Product category tree ,Department tree, stock location tree.
    超级方便的查询，树状视图。
    增加 ztree_root_id 参数自定义根节点
    """,
    'price': 108.00,
    'currency': 'EUR',
    'depends': [
        'web',
        # 'product',
    ],
    'images': ['static/description/banner.gif'],
    'data': [
        'views/ztree_templates.xml',
        # 'views/product_views.xml',
    ],
    'qweb': [
        "static/src/xml/ztree.xml",
    ],
    'demo': [
    ],
    'test': [
    ],
    'css': [
    ],
    'js': [
    ],
    'post_load': None,
    'post_init_hook': None,
    'installable': True,
    'application': True,
    'auto_install': True,
}

