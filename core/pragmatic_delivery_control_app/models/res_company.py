from odoo import models, fields, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    company_delivery_rate = fields.Float("Delivery Rate")
    company_delivery_product = fields.Many2one('product.product',"Delivery Product")