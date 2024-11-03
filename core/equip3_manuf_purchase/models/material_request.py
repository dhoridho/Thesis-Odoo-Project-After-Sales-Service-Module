from odoo import models, fields, api, _


class MaterialRequest(models.Model):
    _inherit = 'material.request'

    material_purchase_id = fields.Many2one(
        'mrp.material.purchase',
        string='MRP Material Purchase',
        copy=False,
    )
