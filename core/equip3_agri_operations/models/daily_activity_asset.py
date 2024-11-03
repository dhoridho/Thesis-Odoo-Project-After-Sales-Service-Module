from odoo import models, fields, api, _


class PlantationAsset(models.Model):
    _name = 'agriculture.daily.activity.asset'
    _description = 'Plantation Asset'

    @api.depends('daily_activity_id', 'daily_activity_id.line_ids')
    def _compute_allowed_activity_lines(self):
        for record in self:
            line_ids = []
            if record.daily_activity_id:
                line_ids = record.daily_activity_id.line_ids.ids
            record.allowed_activity_line_ids = [(6, 0, line_ids)]

    activity_line_sequence = fields.Integer()

    allowed_activity_line_ids = fields.Many2many('agriculture.daily.activity.line', compute=_compute_allowed_activity_lines)

    daily_activity_id = fields.Many2one('agriculture.daily.activity', string='Plantation Plan')
    activity_line_id = fields.Many2one('agriculture.daily.activity.line', string='Plantation Lines')
    activity_record_id = fields.Many2one('agriculture.daily.activity.record', string='Plantation Record')

    activity_asset_id = fields.Many2one('crop.activity.asset', string='Activity Asset')
    activity_id = fields.Many2one('crop.activity', related='activity_asset_id.activity_id')

    asset_id = fields.Many2one('maintenance.equipment', string='Line Asset', required=True)
    user_id = fields.Many2one('res.users', string='Line Responsible', required=True)
    original_move = fields.Boolean(copy=False)
