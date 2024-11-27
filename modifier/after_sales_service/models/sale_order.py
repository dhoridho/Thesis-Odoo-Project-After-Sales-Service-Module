from datetime import timedelta
from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    warranty_expire_date = fields.Date(string='Warranty Expire Date', compute='_compute_warranty_expire_date', store=True, readonly=True)

    @api.depends('order_id.date_order', 'product_id.warranty_period_id')
    def _compute_warranty_expire_date(self):
        for line in self:
            if line.product_id and line.product_template_id.warranty_period_id:
                line.warranty_expire_date = line.order_id.date_order + timedelta(days=line.product_template_id.warranty_period_id.duration)
            else:
                line.warranty_expire_date = False
