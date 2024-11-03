
from odoo import api , models, fields 
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class ComputeCompleteDate(models.TransientModel):
    _name = 'compute.complete.date'

    date = fields.Datetime('Investigation Finsihed Date', default=datetime.now())
    record_id = fields.Many2one('investigation.record', string='Investigation Record')

    def action_confirm(self):
        self.record_id.write({'complete_datetime': self.date,
                              'state': 'complete'})
