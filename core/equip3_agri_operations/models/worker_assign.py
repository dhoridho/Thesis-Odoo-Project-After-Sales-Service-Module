from odoo import models, fields, api, _


class AgricultureWorkerAssign(models.Model):
    _name = 'agriculture.worker.assign'
    _description = 'Worker Assign'

    @api.depends('activity_line_id')
    def _compute_allowed_activity_records(self):
        for record in self:
            activity_record_ids = record.activity_line_id.workorder_ids
            allowed_activity_records = activity_record_ids.filtered(lambda w: w.state not in ('done', 'cancel'))
            record.allowed_activity_record_ids = [(6, 0, allowed_activity_records.ids)]

    daily_activity_id = fields.Many2one('agriculture.daily.activity', string='Daily Activity', readonly=True)
    activity_line_id = fields.Many2one('agriculture.daily.activity.line', string='Activity Line', readonly=True)
    allowed_activity_record_ids = fields.Many2many('agriculture.daily.activity.record', compute=_compute_allowed_activity_records)
    activity_record_id = fields.Many2one('agriculture.daily.activity.record', string='Activity Record', required=True, readonly=True, domain="[('id', 'in', allowed_activity_record_ids)]")
    worker_id = fields.Many2one('hr.employee', string='Worker', required=True, domain="[('active', '=', True)]", readonly=True)
