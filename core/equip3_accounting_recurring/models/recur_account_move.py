from odoo import models, fields, api
from odoo.exceptions import UserError

class RecurAccountMove(models.Model):
    _inherit = 'account.move'

    is_prepayment = fields.Boolean(string='Prepayment')