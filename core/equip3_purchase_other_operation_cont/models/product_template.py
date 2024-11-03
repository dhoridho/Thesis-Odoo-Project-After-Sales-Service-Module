
from odoo import models, fields, api, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    can_be_direct = fields.Boolean(
        string='Can be Direct Purchased',
        copy=True,
    )