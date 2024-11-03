from odoo import fields, models, api, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    rfm_segment_id = fields.Many2one("setu.rfm.segment", "RFM Segment")