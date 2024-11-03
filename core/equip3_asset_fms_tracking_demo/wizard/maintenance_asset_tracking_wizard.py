from odoo import api, fields, models
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta



class MaintenanceAssetTrackingWizard(models.TransientModel):
    _name = 'maintenance.asset.tracking.wizard'
    _description = 'Asset Tracking'

    name = fields.Char(string='Name', default='Asset Tracking')
    history_type = fields.Selection([
        ('today', 'Today'),
        ('yesterday', 'Yesterday'),
        ('3_days', 'Last 3 days'),
    ], string='History', default="today")
    start_date = fields.Date('Start Date', default=datetime.today())
    end_date = fields.Date('End Date', default=datetime.today())

    @api.onchange('history_type')
    def _onchange_history_type(self):
        for rec in self:
            if rec.history_type == 'today':
                rec.start_date = datetime.today()
                rec.end_date = datetime.today()
            elif rec.history_type == 'yesterday':
                rec.start_date =  datetime.today() - relativedelta(days=1)
                rec.end_date =  datetime.today() - relativedelta(days=1)
            elif rec.history_type == '3_days':
                rec.start_date =  datetime.today() - relativedelta(days=3)
                rec.end_date =  datetime.today()

