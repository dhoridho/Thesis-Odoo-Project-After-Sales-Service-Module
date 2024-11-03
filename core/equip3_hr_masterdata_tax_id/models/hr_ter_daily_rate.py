from odoo import fields, models, api, _

class HrTERDailyRate(models.Model):
    _name = 'hr.ter.daily.rate'
    _inherit = ['mail.thread']
    _description = 'HR TER Daily Rate'

    daily_bruto_income_from = fields.Float('Daily Bruto Income From', group_operator=False)
    daily_bruto_income_to = fields.Float('Daily Bruto Income To', group_operator=False)
    daily_rate = fields.Float('Rate (%)', group_operator=False)