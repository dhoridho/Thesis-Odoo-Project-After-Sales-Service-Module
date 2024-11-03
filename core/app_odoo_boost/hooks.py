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
    """
    数据初始化，只在安装时执行，更新时不执行
    """
    try:
        env = api.Environment(cr, SUPERUSER_ID, {})
        # # 配置默认值
        vlist = [{
            'key': 'app_stop_subscribe',
            'value': 'False',
        }]
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

def post_init_hook(cr, registry):
    try:
        env = api.Environment(cr, SUPERUSER_ID, {})
        ids = []
        ids.append(env.ref('mail.ir_cron_mail_scheduler_action', raise_if_not_found=False))
        ids.append(env.ref('mail.ir_cron_delete_notification', raise_if_not_found=False))
        ids.append(env.ref('mail.ir_cron_mail_notify_channel_moderators', raise_if_not_found=False))
        ids.append(env.ref('mail.ir_cron_mail_notify_channel_moderators', raise_if_not_found=False))
        ids.append(env.ref('fetchmail.ir_cron_mail_gateway_action', raise_if_not_found=False))
        ids.append(env.ref('snailmail.snailmail_print', raise_if_not_found=False))
        ids.append(env.ref('account.ir_cron_auto_post_draft_entry', raise_if_not_found=False))
        ids.append(env.ref('account_online_sync.online_sync_cron', raise_if_not_found=False))
        ids.append(env.ref('account_invoice_extract.ir_cron_update_ocr_status', raise_if_not_found=False))
        ids.append(env.ref('partner_autocomplete.ir_cron_partner_autocomplete', raise_if_not_found=False))
        ids.append(env.ref('auth_signup.ir_cron_auth_signup_send_pending_user_reminder', raise_if_not_found=False))
        ids.append(env.ref('hr_contract.ir_cron_data_contract_update_state', raise_if_not_found=False))
        ids.append(env.ref('sms.ir_cron_sms_scheduler_action', raise_if_not_found=False))
        # ids.append(env.ref('payment.cron_post_process_payment_tx', raise_if_not_found=False))
        ids.append(env.ref('digest.ir_cron_digest_scheduler_action', raise_if_not_found=False))
        ids.append(env.ref('maintenance.maintenance_requests_cron', raise_if_not_found=False))
        for cron in ids:
            if cron:
                cron.write({
                    'active': False,
                })
    except Exception as e:
        raise Warning(e)

def uninstall_hook(cr, registry):
    """
    数据初始化，卸载时执行
    """
    pass

