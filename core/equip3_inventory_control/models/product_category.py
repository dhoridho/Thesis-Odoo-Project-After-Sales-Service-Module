
from odoo import models, fields, api, _


class ProductCategory(models.Model):
    _inherit = 'product.category'

    stock_scrap_account = fields.Many2one(
        'account.account', domain=[('user_type_id.name', 'ilike', 'Expenses')], string="Stock Scrap Account", tracking=True)


# class ProductTemplate(models.Model):
#     _inherit = 'product.template'

#     is_low_stock = fields.Boolean(string="Is Low Stock")


# class Product(models.Model):
#     _inherit = 'product.product'

#     product_display_name = fields.Char(
#         string='Product Display Name', compute='_compute_product_display_name', store=True)
#     is_low_stock = fields.Boolean(string="Is Low Stock")

#     @api.depends('name', 'default_code')
#     def _compute_product_display_name(self):
#         for record in self:
#             if isinstance(record.id, models.NewId):
#                 record.product_display_name = ''
#             else:
#                 record.product_display_name = record.display_name or ''
