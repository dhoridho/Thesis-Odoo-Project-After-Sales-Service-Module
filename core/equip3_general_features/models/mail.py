# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, exceptions, fields, models, _
import urllib.parse

class MailThread(models.AbstractModel):

    _inherit = 'mail.thread'


    def _notify_get_action_link(self, link_type, **kwargs):
        """ Prepare link to an action: view document, follow document, ... """
        res = super(MailThread, self)._notify_get_action_link(link_type, **kwargs)
        base_url = self[0].get_base_url()
        res = res.replace(base_url,'')
        res = base_url+ '/web?db='+self._cr.dbname+'&redirect='+urllib.parse.quote(res, safe='')
        return res



class MailTemplate(models.Model):
    _inherit = 'mail.template'


    def send_mail(self, res_id, force_send=False, raise_exception=False, email_values=None, notif_layout=False):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        if self._context.get('url'):
            old_url = self._context['url']
            new_url = base_url+ '/web?db='+self._cr.dbname+'&redirect='+urllib.parse.quote(old_url, safe='')
            self.env.context = dict(self.env.context)
            self.env.context.update({'url': new_url})
        res = super(MailTemplate, self).send_mail(res_id, force_send, raise_exception, email_values, notif_layout)

        return res


