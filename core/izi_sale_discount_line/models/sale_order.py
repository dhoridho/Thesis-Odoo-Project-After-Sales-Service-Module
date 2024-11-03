from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import math

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    price_retail = fields.Float('Retail Price')
    price_discount = fields.Float('Disc.')

    def _prepare_invoice_line(self, **optional_values):
        self.ensure_one()
        res = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
        if self.price_retail:
            res['price_retail'] = self.price_retail
        if self.price_discount:
            res['price_discount'] = self.price_discount
        return res