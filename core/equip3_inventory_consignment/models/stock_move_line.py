from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import OrderedSet
from odoo.tools.float_utils import float_compare, float_is_zero, float_round

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    is_consignment = fields.Boolean('Is Consignment')
