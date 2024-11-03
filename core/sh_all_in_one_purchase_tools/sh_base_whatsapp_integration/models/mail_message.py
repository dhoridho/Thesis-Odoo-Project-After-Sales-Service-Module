# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api, _
import html2text

class Message(models.TransientModel):
    _inherit = 'mail.compose.message'

    is_wp = fields.Boolean("Is whatsapp ?")

    def action_send_wp(self):
        text = html2text.html2text(self.body)
        phone = self.partner_ids[0].mobile
        base_url = self.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')
        if self.attachment_ids:
            text += '%0A%0A Other Attachments :'
            for attachment in self.attachment_ids:
                attachment.generate_access_token()
                text += '%0A%0A'
                text += base_url+'/web/content/ir.attachment/' + \
                    str(attachment.id)+'/datas?access_token=' + \
                    attachment.access_token
        context = dict(self._context or {})
        active_id = context.get('active_id', False)
        active_model = context.get('active_model', False)

        if text and active_id and active_model:
            message = str(text).replace('*', '').replace('_', '').replace('%0A',
                                                                          '<br/>').replace('%20', ' ').replace('%26', '&')
            if active_model == 'sale.order' and self.env['sale.order'].browse(
                    active_id).company_id.display_in_message:
                self.env['mail.message'].create({
                    'partner_ids': [(6, 0, self.partner_ids.ids)],
                    'model': 'sale.order',
                    'res_id': active_id,
                    'author_id': self.env.user.partner_id.id,
                    'body': message or False,
                    'message_type': 'comment',
                })
            if active_model == 'purchase.order' and self.env['purchase.order'].browse(
                    active_id).company_id.purchase_display_in_message:
                self.env['mail.message'].create({
                    'partner_ids': [(6, 0, self.partner_ids.ids)],
                    'model': 'purchase.order',
                    'res_id': active_id,
                    'author_id': self.env.user.partner_id.id,
                    'body': message or False,
                    'message_type': 'comment',
                })
            if (active_model == 'account.move' and self.env['account.move'].browse(active_id).company_id.invoice_display_in_message) or (active_model == 'account.payment' and self.env['account.payment'].browse(active_id).company_id.invoice_display_in_message):
                self.env['mail.message'].create({
                    'partner_ids': [(6, 0, self.partner_ids.ids)],
                    'model': active_model,
                    'res_id': active_id,
                    'author_id': self.env.user.partner_id.id,
                    'body': message or False,
                    'message_type': 'comment',
                })

            if active_model == 'stock.picking' and self.env['stock.picking'].browse(
                    active_id).company_id.inventory_display_in_message:
                self.env['mail.message'].create({
                    'partner_ids': [(6, 0, self.partner_ids.ids)],
                    'model': 'stock.picking',
                    'res_id': active_id,
                    'author_id': self.env.user.partner_id.id,
                    'body': message or False,
                    'message_type': 'comment',
                })

        return {
            'type': 'ir.actions.act_url',
            'url': "https://web.whatsapp.com/send?l=&phone="+phone+"&text=" + text,
            'target': 'new',
        }
