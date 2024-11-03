# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, _
from odoo.exceptions import UserError


class ShSendWhatsappMessage(models.TransientModel):
    _name = "sh.base.send.whatsapp.message.wizard"
    _description = "Send whatsapp message wizard"

    partner_ids = fields.Many2one("res.partner", string="Recipients")
    message = fields.Text("Message", required=True)
    attachment_ids = fields.Many2many(comodel_name="ir.attachment",
                                      relation="rel_sh_send_whatsapp_msg_ir_attachments",
                                      string="Attachments")

    def action_send_whatsapp_message(self):
        if self:
            for rec in self:
                for partner in rec.partner_ids:
                    active_ids = self.env.context.get('active_ids')
                    active_id = int(active_ids[0])
                    sh_message = ""
                    if rec.message:
                        sh_message = str(self.message).replace(
                            '*', '').replace('_', '').replace('%0A', '<br/>').replace('%20', ' ').replace('%26','&')

                    if partner.mobile:
                        return {
                            'type': 'ir.actions.act_url',
                            'url': "https://web.whatsapp.com/send?l=&phone="+partner.mobile+"&text=" + rec.message.replace('&','%26'),
                            'target': 'new',
                            'res_id': rec.id,
                        }

                    else:
                        raise UserError(_("Partner Mobile Number Not Exist"))
