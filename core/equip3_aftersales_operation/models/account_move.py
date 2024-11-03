from odoo import models, api, fields, _

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    sale_service_line_ids = fields.Many2many('sale.service.line', 'account_move_line_serviceline_rel', 'moveline_id', 'serviceline_id')

class AccountMove(models.Model):
    _inherit = 'account.move'

    sale_service_ids = fields.Many2many(
        'sale.service',
        'account_move_service_rel',
        'move_id',
        'service_id',
        string=_('Sale Service Reference')
    )
    invoice_date = fields.Date(default=fields.Date.context_today)
