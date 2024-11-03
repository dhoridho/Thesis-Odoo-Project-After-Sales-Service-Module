from odoo import models, fields


class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'

    catering_id = fields.Many2one(comodel_name='catering.order', string='Catering')
    catering_line_id = fields.Many2one(comodel_name='catering.order.line', string='Catering Line')


class StockMove(models.Model):
    _inherit = "stock.move"

    package_id = fields.Many2one("product.product", string="Package Product", related='picking_id.catering_line_id.package_id')
