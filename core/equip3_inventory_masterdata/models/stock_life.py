from odoo import api, fields, models

class StockLife(models.Model):
    _name = 'stock.life'
    _description = 'Stock Life'

    product_ids = fields.Many2many('product.product', 'stock_life_product_id_rel', 'product_id',string='Product')
    category_ids = fields.Many2many('product.category', 'stock_life_category_id_rel', 'category_id',string='Product Category')
    minimum_days = fields.Integer(string='Minimum Expiry Days Prior')
    is_customer = fields.Many2one('res.partner', string='Customers')
    branch_ids = fields.Many2many('res.branch', 'stock_life_branch_id_rel', string='Branch', 
                                    default=lambda self: self.env.branches)
    product_id_len = fields.Boolean(string="Product Len", compute="_product_id_len")
    category_id_len = fields.Boolean(string="Category Len", compute="_category_id_len")
    restrict_product = fields.Boolean(string="Restrict Product")

    @api.onchange('product_ids')
    def _product_id_len(self):
        for rec in self:
            if len(rec.product_ids) >= 1:
                rec.product_id_len = True
            else:
                rec.product_id_len = False

    @api.onchange('category_ids')
    def _category_id_len(self):
        for rec in self:
            if len(rec.category_ids) >= 1:
                rec.category_id_len = True
            else:
                rec.category_id_len = False