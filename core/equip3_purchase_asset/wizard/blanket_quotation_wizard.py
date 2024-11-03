
from odoo import api, fields, models, _


class BlanketQuotationLine(models.TransientModel):
    _inherit = 'blanket.quotation.line'
    
    is_assets_orders = fields.Boolean(string="Assets Orders", default=False)
    