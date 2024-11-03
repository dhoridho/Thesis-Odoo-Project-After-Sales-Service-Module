# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class CustomCrmLeadLost(models.TransientModel):
    _inherit = 'crm.lead.lost'


    def action_lost_reason_apply(self):
        res = super(CustomCrmLeadLost, self).action_lost_reason_apply()
        leads = self.env['crm.lead'].browse(self.env.context.get('active_ids'))
        lost_stage = self.env['crm.stage'].search([('is_lost','=',True)], limit=1)
        for rec in leads:
            rec.stage_id = lost_stage.id
            rec.active = False
        return res