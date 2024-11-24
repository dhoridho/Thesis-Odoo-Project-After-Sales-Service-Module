from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import json


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"
    _order = 'move_line_sequence asc'

    @api.model
    def default_get(self, fields):
        res = super(StockMoveLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'move_line_ids_without_package' in context_keys:
                if len(self._context.get('move_line_ids_without_package')) > 0:
                    next_sequence = len(self._context.get(
                        'move_line_ids_without_package')) + 1
            res.update({'move_line_sequence': next_sequence})
            if 'move_line_nosuggest_ids' in context_keys:
                if len(self._context.get('move_line_nosuggest_ids')) == 0:
                    next_sequence = len(self._context.get(
                        'move_line_nosuggest_ids')) + 1
            res.update({'move_line_sequence': next_sequence})
        return res

    sequence = fields.Char(string='Sequence')
    move_line_sequence = fields.Integer(string='No')
    product_type = fields.Selection(related='product_id.type')
    quant_package_ids = fields.Many2many(
        'stock.quant.package', compute='_compute_quant_package_ids', store=False)
    result_package_id = fields.Many2one(domain="[]")
    is_quant_update = fields.Boolean(string='Quant Update')

    """ Technical field, only used in detailed operations to reserve quantities """
    force_to_reserve_qty = fields.Float(digits='Product Unit of Measure')

    source_picking_id = fields.Many2one(
        'stock.picking', related='move_id.source_picking_id', string="Source Picking")
    source_move_id = fields.Many2one('stock.move', string="Source Move")
    is_batch_shipping_packing = fields.Boolean(
        string="Is Batch Shipping Packing", related='move_id.is_batch_shipping_packing')
    is_batch_shipping_delivery = fields.Boolean(
        string="Is Batch Shipping Delivery", related='move_id.is_batch_shipping_delivery')
    price_unit = fields.Float('Unit Price', help="Technical field used to record the product cost set by the user during a picking confirmation (when costing "
        "method used is 'average price' or 'real'). Value given in company currency and in product uom.", copy=False)

    svl_source_line_id = fields.Many2one('stock.valuation.layer.line', string='Valuation Line Source')
    svl_source_id = fields.Many2one(related='svl_source_line_id.svl_id')
    lot_id_domain = fields.Char(string='Lot ID Domain', compute='_compute_lot_id_domain')    

    def _reservation_is_updatable(self, quantity, reserved_quant):
        self.ensure_one()
        if self.env.context.get('force_lot_assign', False) and self.move_id._should_force_assign():
            return (self.location_id.id == reserved_quant.location_id.id and
                    self.lot_id.id == reserved_quant.lot_id.id and
                    self.package_id.id == reserved_quant.package_id.id and
                    self.owner_id.id == reserved_quant.owner_id.id)
        return super(StockMoveLine, self)._reservation_is_updatable(quantity, reserved_quant)

    @api.depends('location_dest_id', 'product_id')
    def _compute_quant_package_ids(self):
        for record in self:
            if record.move_id.picking_code == 'incoming':
                package_ids = self.env['stock.quant.package'].search([('location_id', '=', record.location_dest_id.id),
                                                                      ('packaging_id', 'in',
                                                                       record.product_id.packaging_ids.ids)])
            else:
                package_ids = self.env['stock.quant.package'].search(
                    ['|', '|', ('location_id', '=', False), ('location_id', '=', record.location_dest_id.id),
                     ('id', '=', record.package_id.id)])
            record.quant_package_ids = [(6, 0, package_ids.ids)]

    def unlink(self):
        ids_to_delete = self.filtered(lambda r: r.move_id.picking_code == 'incoming').ids

        if ids_to_delete:
            query = 'DELETE FROM stock_move_line WHERE id IN %s'
            self.env.cr.execute(query, (tuple(ids_to_delete),))

            for record in self:
                if record.move_id and record.move_id.next_lot:
                    record.move_id.next_lot = False
            return

        pickings = self.mapped('picking_id')

        result = super(StockMoveLine, self).unlink()
        
        for picking in pickings:
            picking._reset_sequence()
        
        return result


    @api.onchange('sequence')
    def set_sequence_line(self):
        for record in self:
            record.picking_id._reset_sequence()

    @api.onchange('lot_id', 'qty_done', 'location_id')
    def _onchange_available_quantity(self):
        qty_can_minus = self.env['ir.config_parameter'].sudo().get_param(
            'qty_can_minus', False)
        if qty_can_minus:
            for record in self.filtered(lambda r: r.picking_code != 'incoming'):
                available_qty = self.env['stock.quant']._get_available_quantity(
                    record.product_id,
                    record.location_id,
                    lot_id=record.lot_id,
                    package_id=record.package_id,
                    owner_id=record.owner_id,
                    strict=True
                )
                if record.product_uom_id._compute_quantity(record.qty_done, record.product_id.uom_id) > available_qty:
                    raise ValidationError(_('Done qty is greater than the available stock'))

    @api.depends('location_id', 'product_id')
    def _compute_lot_id_domain(self):
        StockQuant = self.env['stock.quant']
        for record in self:
            if record.location_id and record.product_id:
                available_lots_serials = StockQuant._get_available_lots(
                    location_id=record.location_id.id, 
                    product_id=record.product_id.id
                ).mapped('lot_id.id')
                record.lot_id_domain = json.dumps([('id', 'in', available_lots_serials)])
            else:
                record.lot_id_domain = json.dumps([('id', 'in', [])])
