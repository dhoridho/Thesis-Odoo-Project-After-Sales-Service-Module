from odoo import fields,api,models
import mimetypes

class DamageCostLine(models.Model):
    _name = "rental.order.damage.cost.line"
    _description = "Rental Damage Cost Line"
    
    lot_id = fields.Many2one(
        comodel_name='stock.production.lot',
        string='Serial Number',
        domain="[('id', 'in', lot_ids)]"
    )
    lot_ids = fields.Many2many(
        comodel_name='stock.production.lot',
        compute='_compute_lot_ids_damage_cost',
        string='Allowed Serial Numbers',
        store=False
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        compute="_compute_product_id_damage_cost",
        store=True
    )
    damage_notes = fields.Text("Damage Notes")
    attachment = fields.Binary("Attachment")
    attachment_name = fields.Char("Attachment Name", compute="_compute_attachment_name", default="", store=True)
    damage_cost = fields.Float("Damage Cost")
    rental_order_id = fields.Many2one('rental.order', string="Rental Order")
    stock_picking_id = fields.Many2one('stock.picking', string="Stock Picking")
    picking_type_code = fields.Selection(related='stock_picking_id.picking_type_code')

    @api.depends('attachment')
    def _compute_attachment_name(self):
        for record in self:
            if record.attachment:
                record.attachment_name = "Attachment Damage File"

    @api.depends('lot_id')
    def _compute_product_id_damage_cost(self):
        for line in self:
            if line.lot_id:
                line.product_id = line.lot_id.product_id.id

    @api.depends('rental_order_id.checklist_line_ids.lot_id', 'stock_picking_id.checklist_line_rental.lot_id')
    def _compute_lot_ids_damage_cost(self):
        for line in self:
            if line.picking_type_code in ['outgoing', 'incoming']:
                line.lot_ids = line.stock_picking_id.mapped('checklist_line_rental.lot_id')
            else:
                line.lot_ids = line.rental_order_id.mapped('checklist_line_ids.lot_id')