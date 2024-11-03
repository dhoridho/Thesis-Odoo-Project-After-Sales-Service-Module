from odoo import tools, models, fields, api, _ 
from odoo.exceptions import UserError, ValidationError

class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _prepare_invoice(self):
        res = super(SaleOrder,self)._prepare_invoice()
        res['sale_order_ids'] = [(4, self.id)]
        return res
