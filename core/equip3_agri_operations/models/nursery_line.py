from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class NurseryLine(models.Model):
    _inherit = 'agriculture.daily.activity.line'

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New') and 'daily_activity_id' not in vals and vals.get('daily_activity_type') == 'nursery':
            vals['name'] = self.env['ir.sequence'].next_by_code('agriculture.nursery.line') or _('New')
        return super(NurseryLine, self).create(vals)

    def write(self, vals):
        if vals.get('state') == 'confirm' and vals.get('daily_activity_id', self.daily_activity_id) and vals.get('daily_activity_type', self.daily_activity_type) == 'nursery':
            vals['name'] = self.env['ir.sequence'].next_by_code('agriculture.daily.activity.line') or _('New')
        return super(NurseryLine, self).write(vals)

    @api.depends('state', 'activity_type', 'activity_record_ids', 'activity_record_ids.state')
    def _compute_show_actualization_button(self):
        for record in self:
            show_button = record.state in ('confirm', 'progress')
            if show_button and record.activity_type == 'transfer':
                show_button = len(record.activity_record_ids.filtered(lambda r: r.state == 'confirm')) == 0
            record.show_actualization_button = show_button

    daily_activity_type = fields.Selection(selection_add=[('nursery', 'Nursery')], ondelete={'nursery': 'cascade'})
    show_actualization_button = fields.Boolean(compute=_compute_show_actualization_button)

    def action_actualization(self):
        action = super(NurseryLine, self).action_actualization()
        if self.daily_activity_type == 'nursery':
            action['name'] = _('Nursery Record')
            action['views'] = [(self.env.ref('equip3_agri_operations.view_nursery_record_form').id, 'form')]
        return action
