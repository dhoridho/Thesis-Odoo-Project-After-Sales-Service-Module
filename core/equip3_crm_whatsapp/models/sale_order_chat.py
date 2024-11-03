# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import pytz

from odoo import _, api, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def create(self, vals):

        res_chat = super(SaleOrder, self).create(vals)
        contact_id = self.env['acrux.chat.conversation'].search([('res_partner_id', '=', res_chat.partner_id.id)], limit=1)
        chat_content = self.env['acrux.chat.message'].search([('contact_id', '=', contact_id.id), ('ttype', '!=', 'info')], order="id asc")
        if chat_content:
            msg_str = ""
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz)
            for so_chat in chat_content:
                chat_text = ""
                user_name = ""
                if so_chat.ttype == "location":
                    chat_text = so_chat.text.rsplit('\n', 1)[0]
                elif so_chat.ttype == "product":
                    product_id = self.env['product.product'].search([('id', '=', so_chat.res_id)])
                    chat_text = product_id.product_display_name
                else:
                    chat_text = so_chat.text

                if so_chat.from_me:
                    user_name = so_chat.user_id.name
                else:
                    user_name = so_chat.contact_id.name

                # msg_str += "<ul><li><strong>User:</strong> " + user_name + "<li><strong>Content:</strong> " + chat_text + "<li><strong>Date:</strong> " + str(
                # so_chat.date_message) + "</li></ul>"
                time_in_timezone = pytz.utc.localize(so_chat.date_message).astimezone(user_tz)
                msg_str += "[" + time_in_timezone.strftime('%m/%d, %I:%M %p') + "] " + user_name + ": " + chat_text + "<br>"

            res_chat.message_post(body=_(msg_str))

        return res_chat
