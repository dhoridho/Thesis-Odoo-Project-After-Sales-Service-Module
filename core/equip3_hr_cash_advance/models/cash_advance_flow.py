from odoo import api, fields, models


class HrCashAdvanceFlow(models.Model):
    _name = 'hr.cash.advance.flow'
    _description = 'Cash Advance Flow'

    name = fields.Char(string='Name', default='Cash Advance Flow')

    def action_none(self):
        return False
