# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime


class crm_lead_age(models.Model):
    _inherit = 'crm.lead'

    age_audit = fields.One2many('lead.age.audit', 'lead_id', index=True, store=True)

    @api.model
    def set_create_date_for_old_lead(self):
        self._cr.execute("""INSERT INTO lead_age_audit (lead_id, date_in, stage_id)
            SELECT p.id, p.create_date,r.id FROM crm_lead p
            left join crm_stage r on (r.id=p.stage_id)
            WHERE p.probability != 100 and p.probability != 0""")

    # Override Create Function
    @api.model
    def create(self, values):
        line = super(crm_lead_age, self).create(values)
        line.age_audit.create({'lead_id': line.id,
                               'stage_id': line.stage_id.id,
                               'date_in': fields.date.today()})
        return line

    # Override Write Function
    def write(self, vals):
        res = super(crm_lead_age, self).write(vals)
        if 'stage_id' in vals:
            for rec in self.age_audit:
                if not rec.date_out:
                    rec.date_out = fields.date.today()
            if 'probability' in vals:
                if vals['probability'] != 100 and vals['probability'] != 0:
                    self.age_audit.create({'lead_id': self.id,
                                           'stage_id': self.stage_id.id,
                                           'date_in': fields.date.today()})
            if 'probability' not in vals:
                self.age_audit.create({'lead_id': self.id,
                                       'stage_id': self.stage_id.id,
                                       'date_in': fields.date.today()})
        return res

    # Override method for lead restore
    def toggle_active(self):
        for record in self:
            record.active = not record.active
            if record.probability == 100 or record.probability == 0:
                record.age_audit.create({'lead_id': record.id,
                                         'stage_id': record.stage_id.id,
                                         'date_in': fields.date.today()})


class crm_lead_age_audit(models.Model):
    _name = 'lead.age.audit'

    lead_id = fields.Many2one('crm.lead')
    stage_id = fields.Many2one('crm.stage')
    date_in = fields.Date()
    date_out = fields.Date()
    days = fields.Integer(compute='_compute_days', store=True)

    @api.depends('date_in', 'date_out')
    def _compute_days(self):
        self.days = 0
        for res in self:
        
            if res.date_in and res.date_out:
                res.days = (res.date_out - res.date_in).days


class crm_stage(models.Model):
    _inherit = 'crm.stage'

    check = fields.Boolean('Exclude From lifetime Report', store=True)


class CustomCrmLeadLost(models.TransientModel):
    _inherit = 'crm.lead.lost'

    def action_lost_reason_apply(self):
        leads = self.env['crm.lead'].browse(self.env.context.get('active_ids'))
        for rec in leads.age_audit:
            if not rec.date_out:
                rec.date_out = fields.date.today()
        res = super(CustomCrmLeadLost, self).action_lost_reason_apply()
        return res
