from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class NurseryPlan(models.Model):
    _inherit = 'agriculture.daily.activity'

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New') and vals.get('daily_activity_type') == 'nursery':
            vals['name'] = self.env['ir.sequence'].next_by_code('agriculture.nursery.plan') or _('New')
        return super(NurseryPlan, self).create(vals)

    daily_activity_type = fields.Selection(selection_add=[('nursery', 'Nursery')], ondelete={'nursery': 'cascade'})
