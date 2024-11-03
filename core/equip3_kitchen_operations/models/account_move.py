from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    kitchen_id = fields.Many2one('kitchen.production.record', string='Kitchen Production', copy=False)
