from odoo import models, fields, api, _

class ProductTemplateWrranty(models.Model):
    _inherit = 'product.template'

    warranty_type = fields.Selection(string='Warranty Type', selection=[('free', 'Free'), ('paid', 'Paid'),])
