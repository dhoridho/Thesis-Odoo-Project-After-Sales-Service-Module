from odoo import models, fields


class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    catering_id = fields.Many2one(comodel_name='catering.order', string='Catering')

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    catering_id = fields.Many2one('catering.order', related='move_id.catering_id', store=True)
    
