from odoo import api, fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    property_account_debitor_price_difference_categ = fields.Many2one(
        'account.account', string="Loss Price Difference Account",
        company_dependent=True,
        help="This account will be used to value price difference between purchase price and accounting cost.", tracking=True)
