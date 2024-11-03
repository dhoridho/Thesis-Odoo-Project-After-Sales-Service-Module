# -*- coding: utf-8 -*-
from odoo import models
from odoo import fields


class AcruxChatConversation(models.Model):
    _inherit = 'acrux.chat.conversation'

    crm_lead_id = fields.Many2one('crm.lead', 'Lead', ondelete='set null')

    def get_fields_to_read(self):
        out = super(AcruxChatConversation, self).get_fields_to_read()
        out.extend(['crm_lead_id'])
        return out

    def save_crm_lead(self, crm_lead_id):
        self.ensure_one()
        self.write({'crm_lead_id': crm_lead_id})
        lead_id = self.env['crm.lead'].browse(crm_lead_id)
        lead_id.conversation_id = self.id
        return [self.crm_lead_id.id, self.crm_lead_id.name]
