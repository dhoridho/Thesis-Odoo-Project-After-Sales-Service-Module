from odoo import api, fields, models, _


class TransferLogActivity(models.Model):
    _name = 'transfer.log.activity'
    _description = 'Transfer Log Activity'

    action = fields.Char(string="Action")
    reference = fields.Many2one(
        'stock.picking', string='Reference', readonly=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('approved', 'Approved'),
                              ('rejected', 'Rejected'),
                              ('waiting', 'Waiting Another Operation'),
                              ('confirmed', 'Waiting'),
                              ('assigned', 'Ready'),
                              ('done', 'Done'),
                              ('cancel', 'Cancelled'),
                              ("deployed", "Deployed"), ],
                             string="Status", default="draft")
    timestamp = fields.Datetime(string="Timestamp")
    user_id = fields.Many2one('res.users', string="User")
    process_time = fields.Char(string="Processed")
    process_time_hours = fields.Float(string="Processed Time Hours")
    process_days = fields.Float(string='Processed Days')
