
from odoo import _, api, fields, models


class StockPickingBatchValidate(models.TransientModel):
    _name = 'stock.picking.batch.validate'
    _description = "Stock Picking Batch Validate"

    name = fields.Char(string="Reference")
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")
    scheduled_date = fields.Date(string="Scheduled Date")
    user_id = fields.Many2one('res.users', string="Responsible")
    stock_line = fields.One2many(
        'stock.picking.batch.validate.line', 'line_id', string="Stock Line")

    def action_confirm(self):
        context = dict(self.env.context) or {}
        picking_id = self.env['stock.picking.batch'].browse(
            [context.get('active_id')])
        for move_line in picking_id.move_line_ids:
            move_line.qty_done = move_line.product_uom_qty
        for move in picking_id.move_ids:
            move.quantity_done = move.product_uom_qty
        picking_id.action_force_validate()


class StockPickingBatchValidateLine(models.TransientModel):
    _name = 'stock.picking.batch.validate.line'
    _description = "Stock Picking Batch Validate Data"

    line_id = fields.Many2one(
        'stock.picking.batch.validate', string="Stock Batch Validate")
    product_id = fields.Many2one('product.product', string="Product")
    transfer_id = fields.Many2one('stock.picking', string="Transfer")
    location_id = fields.Many2one('stock.location', string="Source Location")
    product_uom_qty = fields.Float(string='Demanded')
    reserved_availability = fields.Float(string="Reserved Avaibitity")
    quantity_done = fields.Float(
        compute='_calculate_done_qty', store=True, string="Done")

    @api.depends('reserved_availability', 'product_uom_qty')
    def _calculate_done_qty(self):
        for record in self:
            record.quantity_done = record.product_uom_qty - record.reserved_availability
