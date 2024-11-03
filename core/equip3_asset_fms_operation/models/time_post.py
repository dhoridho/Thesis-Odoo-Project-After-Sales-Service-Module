
from odoo import api, fields, models, _
from odoo.osv import expression

class TimePost(models.Model):
    _name = 'time.post'
    _description = 'Time Post'

    maintenance_wo_id = fields.Many2one('maintenance.work.order')
    repair_id = fields.Many2one('maintenance.repair.order')
    date_start = fields.Datetime('Start Date', default=fields.Datetime.now, required=True)
    date_end = fields.Datetime('End Date')
    duration = fields.Float('Duration', compute='_compute_duration', store=True)

    @api.depends('date_end', 'date_start')
    def _compute_duration(self):
        for blocktime in self:
            if blocktime.date_start and blocktime.date_end:
                d1 = fields.Datetime.from_string(blocktime.date_start)
                d2 = fields.Datetime.from_string(blocktime.date_end)
                diff = d2 - d1
                blocktime.duration = round(diff.total_seconds() / 60.0, 2)
            else:
                blocktime.duration = 0.0
