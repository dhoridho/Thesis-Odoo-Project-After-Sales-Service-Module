
from odoo import _, api, fields, models

class SaleOrderDeduction(models.Model):
    _name = 'sale.order.deduction'
    _description = 'Sale Order Deduction'

    product_id = fields.Many2one('product.template', string="Product")
    sale_id = fields.Many2one('sale.order', string='Sale Order')
    description = fields.Text(string='Description')
    product_qty = fields.Float(string='Quantity')
    product_price = fields.Float(string='Unit Price')
    product_total = fields.Float(string='Total', compute="_compute_product_total", store=True)


    @api.depends('product_price','product_qty')
    def _compute_product_total(self):
        for rec in self:
            rec.product_total = rec.product_price * rec.product_qty
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.description = self.product_id.name
