# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import pytz

from odoo import _, api, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    @api.model
    def create(self, vals):

        res_chat = super(CrmLead, self).create(vals)
        chat_content = self.env['acrux.chat.message'].search([('contact_id', '=', res_chat.conversation_id.id), ('ttype', '!=', 'info')], order="id asc")

        if chat_content:
            msg_str = ""
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz)

            for crm_chat in chat_content:
                chat_text = ""
                if crm_chat.ttype == "location":
                    chat_text = crm_chat.text.rsplit('\n', 1)[0]
                elif crm_chat.ttype == "product":
                    product_id = self.env['product.product'].search([('id', '=', crm_chat.res_id)])
                    chat_text = product_id.product_display_name
                else:
                    chat_text = crm_chat.text

                if crm_chat.from_me:
                    user_name = crm_chat.user_id.name
                else:
                    user_name = crm_chat.contact_id.name

                # msg_str += "<ul><li><strong>User:</strong> " + user_name + "<li><strong>Content:</strong> " + chat_text + "<li><strong>Date:</strong> " + str(
                # crm_chat.date_message) + "</li></ul>"

                time_in_timezone = pytz.utc.localize(crm_chat.date_message).astimezone(user_tz)
                msg_str += "[" + time_in_timezone.strftime('%m/%d, %I:%M %p') + "] " + user_name + ": " + chat_text + "<br>"

            res_chat.message_post(body=_(msg_str))
        return res_chat

