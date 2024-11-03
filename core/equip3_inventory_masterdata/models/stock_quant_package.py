
import re
from odoo import models, fields, api, _


class StockQuantPackage(models.Model):
    _inherit = 'stock.quant.package'

    color = fields.Integer('Color Index')
    # package_status = fields.Selection([
    #     ('packed', 'Packed'),
    #     ('partial', 'Partial'),
    #     ('empty', 'Empty')
    # ], 'Status', compute="_compute_package_staus", store=True)
    qty = fields.Float(string="Quantity", compute="_compute_qty_uom", store=True)
    uom_id = fields.Many2one('uom.uom', string="uom", compute="_compute_qty_uom", store=True)
    
    @api.depends('quant_ids', 'quant_ids.quantity')
    def _compute_qty_uom(self):
        for record in self:
            record.uom_id = record.quant_ids and record.quant_ids[0].product_uom_id.id or False
            record.qty = sum(record.quant_ids.mapped('quantity'))

    @api.model
    def action_package_unpack(self, vals):
        pass
