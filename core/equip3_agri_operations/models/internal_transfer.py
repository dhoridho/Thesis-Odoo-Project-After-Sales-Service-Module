from odoo import models, fields, api, _


class InternalTransfer(models.Model):
    _inherit = 'internal.transfer'

    agri_harvest_plan_id = fields.Many2one('agriculture.daily.activity', string='Agri Harvest Plan Transfer')
    agri_harvest_line_id = fields.Many2one('agriculture.daily.activity.line', string='Agri Harvest Lines Transfer')
    agri_harvest_record_id = fields.Many2one('agriculture.daily.activity.record', string='Agri Harvest Record Transfer')
