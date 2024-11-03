from odoo import models, fields


class MrpPlan(models.Model):
    _inherit = 'mrp.plan'

    mps_production_id = fields.Many2one('equip.mps.production', string='MPS Production')
    mps_product_id = fields.Many2one('product.product', string='MPS Product')
    mps_product_qty = fields.Float(string='MPS Total Quantity')
    mps_bom_id = fields.Many2one('mrp.bom', string='MPS BOM')
    mps_start_date = fields.Date(string='MPS Start Date')
    mps_end_date = fields.Date(string='MPS End Date')
