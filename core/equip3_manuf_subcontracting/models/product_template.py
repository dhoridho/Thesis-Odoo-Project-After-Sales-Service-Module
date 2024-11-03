from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    manuf_cost_category = fields.Selection(selection_add=[('subcontracting', 'Subcontracting')])
