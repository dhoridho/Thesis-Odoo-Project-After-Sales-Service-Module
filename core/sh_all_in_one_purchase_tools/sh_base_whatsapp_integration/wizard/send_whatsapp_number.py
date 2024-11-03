# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api


class ShSendWhatsappNumber(models.TransientModel):
    _name = "sh.base.send.whatsapp.number.wizard"
    _description = "Send whatsapp message wizard"

    partner_ids = fields.Many2one("res.partner", string="Recipients")
    whatsapp_mobile = fields.Char(string="Whatsapp Number", required=True)
    message = fields.Text("Message", required=True)
    crm_lead_id = fields.Many2one('crm.lead', string="Lead")

    @api.onchange('partner_ids')
    def onchange_partner(self):
        if self.partner_ids:
            self.whatsapp_mobile = self.partner_ids.mobile

    def action_send_whatsapp_number(self):
        if self.whatsapp_mobile and self.message:
            for rec in self:
                if rec.partner_ids:
                    sh_message = ""
                    if self.message:
                        sh_message = str(self.message).replace(
                            '*', '').replace('_', '').replace('%0A', '<br/>').replace('%20', ' ').replace('%26','&')
                    
                    return {
                        'type': 'ir.actions.act_url',
                        'url': "https://web.whatsapp.com/send?l=&phone="+rec.whatsapp_mobile+"&text=" + self.message.replace('&','%26'),
                        'target': 'new',
                        'res_id': self.id,
                    }
