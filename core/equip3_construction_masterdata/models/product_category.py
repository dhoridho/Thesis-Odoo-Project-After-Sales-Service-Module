from odoo import api, fields, models


class ProductCategory(models.Model):
    _inherit = 'product.category'

    coscode = fields.Char(string='Cost Code')
    purchase_action = fields.Many2one('purchase.action', string="Purchase Action")
    analytic_tag_ids = fields.Many2many(
        'account.analytic.tag',
        relation='product_category_analytic_tag_rel',
        string='Analytic Group')