from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    unbuild_id = fields.Many2one('mrp.unbuild')
    consumption_id = fields.Many2one('mrp.consumption', string='Production Record', copy=False)
