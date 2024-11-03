# -*- coding: utf-8 -*-

# Created on 2018-10-12
# author: 广州尚鹏，https://www.sunpop.cn
# email: 300883@qq.com
# resource of Sunpop
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

# Odoo在线中文用户手册（长期更新）
# https://www.sunpop.cn/documentation/user/10.0/zh_CN/index.html

# Odoo10离线中文用户手册下载
# https://www.sunpop.cn/odoo10_user_manual_document_offline/
# Odoo10离线开发手册下载-含python教程，jquery参考，Jinja2模板，PostgresSQL参考（odoo开发必备）
# https://www.sunpop.cn/odoo10_developer_document_offline/
# description:

from odoo import api, SUPERUSER_ID, _


def pre_init_hook(cr):
    pass

def post_init_hook(cr, registry):
    """
    数据初始化，只在安装时执行，更新时不执行
    """
    try:
        env = api.Environment(cr, SUPERUSER_ID, {})
        # # 配置默认值，注意，如果该值为 False，在 odoo 中也是判断该 key 值是 True，只能移除
        vlist = [{
            'key': 'app_default_superbar_lazy_search',
            'value': 'False',
        }, ]
        for v in vlist:
            p = env['ir.config_parameter'].sudo().search([('key', 'like', v['key'])])
            if v['value'] == 'False' and p:
                p.unlink()
            if v['value'] != 'False':
                if p:
                    v.pop('key')
                    p.write(v)
                else:
                    p.create(v)
    except Exception as e:
        raise Warning(e)

def uninstall_hook(cr, registry):
    pass
    # cr.execute("")

