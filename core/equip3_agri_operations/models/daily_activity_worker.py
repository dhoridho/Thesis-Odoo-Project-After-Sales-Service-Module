from odoo import models, fields, api, _


class PlantationWorker(models.Model):
    _name = 'agriculture.daily.activity.worker'
    _description = 'Plantation Worker'
    _rec_name = 'group_id'

    @api.depends('daily_activity_id', 'daily_activity_id.line_ids')
    def _compute_allowed_activity_lines(self):
        for record in self:
            line_ids = []
            if record.daily_activity_id:
                line_ids = record.daily_activity_id.line_ids.ids
            record.allowed_activity_line_ids = [(6, 0, line_ids)]

    allowed_activity_line_ids = fields.Many2many('agriculture.daily.activity.line', compute=_compute_allowed_activity_lines)

    daily_activity_id = fields.Many2one('agriculture.daily.activity', string='Plantation Plan')
    activity_line_id = fields.Many2one('agriculture.daily.activity.line', string='Plantation Lines')
    activity_record_id = fields.Many2one('agriculture.daily.activity.record', string='Plantation Record')

    group_id = fields.Many2one('agriculture.worker.group', string='Group')
    head_id = fields.Many2one('hr.employee', string='Head of Group', domain="[('is_agri_worker', '=', True)]")
    worker_ids = fields.Many2many('hr.employee', string='Workers', required=True, domain="[('is_agri_worker', '=', True)]")
    original_move = fields.Boolean(copy=False)

    @api.onchange('group_id')
    def _onchange_group_id(self):
        head_id = False
        worker_ids = []
        if self.group_id:
            head_id = self.group_id.head_id.id
            worker_ids = self.group_id.worker_ids.ids

        self.head_id = head_id
        self.worker_ids = [(6, 0, worker_ids)]
