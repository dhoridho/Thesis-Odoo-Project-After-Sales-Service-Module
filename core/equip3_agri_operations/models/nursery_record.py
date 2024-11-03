from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class NurseryRecord(models.Model):
    _inherit = 'agriculture.daily.activity.record'

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New') and vals.get('daily_activity_type') == 'nursery':
            vals['name'] = self.env['ir.sequence'].next_by_code( 'agriculture.nursery.record') or _('New')
        return super(NurseryRecord, self).create(vals)

    daily_activity_type = fields.Selection(selection_add=[('nursery', 'Nursery')], ondelete={'nursery': 'cascade'})

    def _should_serialize(self):
        self.ensure_one()
        return super(NurseryRecord, self)._should_serialize() or \
            (self.activity_type == 'planting' and \
                any(nursery.product_id.tracking in ('lot', 'serial') for nursery in self.nursery_ids) and \
                    not self.env.context.get('skip_serializer', False))

    def action_serialize(self):
        res = super(NurseryRecord, self).action_serialize()
        if self.activity_type == 'planting':
            res['res_model'] = 'agri.serializer'
        return res
