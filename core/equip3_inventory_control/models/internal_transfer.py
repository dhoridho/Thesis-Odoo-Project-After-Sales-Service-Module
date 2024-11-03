from odoo import api, fields, models, _


class InternalTransferInherit(models.Model):
    _inherit = 'internal.transfer'

    average_id = fields.Many2one(
        comodel_name='stock.day.average', string='Average')
