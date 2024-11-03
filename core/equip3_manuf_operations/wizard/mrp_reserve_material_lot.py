from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import OrderedSet


class MrpReserveMaterialLot(models.TransientModel):
    _name = 'mrp.reserve.material.lot'
    _description = 'MRP Reserve Material Lot'

    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    mrp_reserve_material_id = fields.Many2one(comodel_name='mrp.reserve.material.line', string='Material Line')
    mrp_rsv_mtr_id = fields.Many2one(comodel_name='mrp.rsv.mtr', string='RSV Material')
    
    line_ids = fields.One2many('mrp.reserve.material.lot.line', 'reserve_id', string='Lines')

    def action_confirm(self):
        self.ensure_one()
        lot_ids = self.line_ids.mapped('lot_id')
        qty = self.line_ids and sum(self.line_ids.mapped('to_reserve_uom_qty')) or 0
        if lot_ids:
            self.mrp_rsv_mtr_id.lot_ids = [(6,0,lot_ids.ids)]
            self.mrp_rsv_mtr_id.to_reserve_uom_qty = qty
            moves = self.line_ids.mapped('mrp_reserve_material_id.move_id')

            StockMove = self.env['stock.move']
            assigned_moves_ids = OrderedSet()
            partially_available_moves_ids = OrderedSet()
            roundings = {move: move.product_id.uom_id.rounding for move in moves}

            for line in self.line_ids.filtered(lambda l:l.product_tracking != 'none'):
                move = line.mrp_reserve_material_id.move_id
                rounding = roundings[move]

                if move.state not in ('confirmed', 'waiting', 'partially_available', 'assigned'):
                    continue
                if move.procure_method == 'make_to_order':
                    continue

                move._do_unreserve()

                """ Here's the change """
                need = move.product_uom._compute_quantity(line.to_reserve_uom_qty, move.product_id.uom_id)

                if need <= 0:
                    continue

                forced_package_id = move.package_level_id.package_id or None
                available_quantity = move._get_available_quantity(move.location_id, package_id=forced_package_id)
                if available_quantity <= 0:
                    continue
                taken_quantity = move._update_reserved_quantity(need, available_quantity, move.location_id, package_id=forced_package_id, strict=False)
                if float_is_zero(taken_quantity, precision_rounding=rounding):
                    continue
                if float_compare(need, taken_quantity, precision_rounding=rounding) == 0 and \
                float_compare(move.product_uom_qty, move.reserved_availability, precision_rounding=rounding) == 0.0:
                    assigned_moves_ids.add(move.id)
                else:
                    partially_available_moves_ids.add(move.id)

            StockMove.browse(partially_available_moves_ids).write({'state': 'partially_available'})
            StockMove.browse(assigned_moves_ids).write({'state': 'assigned'})
            moves.mapped('picking_id')._check_entire_pack()

        return True

    @api.constrains('line_ids')
    def _constrains_lines(self):
        for record in self:
            offset_lines = []
            unavailable_lines = []
            # for line in record.line_ids:
            #     if not line.product_uom_qty >= line.to_reserve_uom_qty >= 0.0:
            #         offset_lines += [_('- %s. To Consume: %s, To Reserve: %s' % (line.product_id.display_name, line.product_uom_qty, line.to_reserve_uom_qty))]
            #     if line.to_reserve_uom_qty > line.availability_uom_qty + line.reserved_uom_qty:
            #         unavailable_lines += [_('- %s on location %s' % (line.product_id.display_name, line.location_id.display_name))] 
            # err_message = []
            # if offset_lines:
            #     err_message += [_('To Reserve must be positive and cannot be bigger than To Consume!\n') + '\n'.join(offset_lines)]
            # if unavailable_lines:
            #     err_message += [_('There is not enough stock for:\n') + '\n'.join(unavailable_lines)]
            # if err_message:
            #     raise UserError('\n\n'.join(err_message))


class MrpReserveMaterialLine(models.TransientModel):
    _name = 'mrp.reserve.material.lot.line'
    _description = 'MRP Reserve Material Line'

    reserve_id = fields.Many2one('mrp.reserve.material.lot', string='Reserve', required=True, ondelete='cascade')
    sequence = fields.Integer()
    product_id = fields.Many2one('product.product', string='Material', related='reserve_id.product_id', store=True)
    mrp_reserve_material_id = fields.Many2one('mrp.rsv.mtr', string='Material Line', related='reserve_id.mrp_rsv_mtr_id')
    product_uom = fields.Many2one('uom.uom', related='mrp_reserve_material_id.product_uom', string='UoM')
    product_uom_qty = fields.Float(digits='Product Unit of Measure', related='mrp_reserve_material_id.product_uom_qty', string='To Consume')
    # availability_uom_qty = fields.Float(digits='Product Unit of Measure', string='Available', compute='_compute_availability_uom')
    reserved_uom_qty = fields.Float(digits='Product Unit of Measure', related='mrp_reserve_material_id.reserved_uom_qty', string='Reserved')
    to_reserve_uom_qty = fields.Float(digits='Product Unit of Measure', string='Quantity', default=1)
    product_tracking = fields.Selection(string='Product Tracking',related="product_id.tracking", store=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', related='mrp_reserve_material_id.warehouse_id')
    location_id = fields.Many2one('stock.location', string='Location', related='mrp_reserve_material_id.location_id')
    production_id = fields.Many2one('mrp.production', string='Manufaturing Order', related='mrp_reserve_material_id.production_id')
    workorder_id = fields.Many2one('mrp.workorder', string='Work Order', related='mrp_reserve_material_id.workorder_id')
    lot_id = fields.Many2one(comodel_name='stock.production.lot', string='Lot/Serial Number',domain="[('product_id','=',product_id)]")
    

    _sql_constraints = [
        ('unique_sequence', 'unique(reserve_id, sequence)', _('The sequence must be unique!'))
    ]

    # @api.depends('move_id', 'reserve_id', 'sequence', 'reserved_uom_qty', 'to_reserve_uom_qty', 'reserve_id.line_ids', 'reserve_id.line_ids.sequence', 
    # 'reserve_id.line_ids.move_id', 'reserve_id.line_ids.to_reserve_uom_qty', 'reserve_id.line_ids.reserved_uom_qty', 'reserve_id.line_ids.availability_uom_qty')
    # def _compute_availability_uom(self):

    #     def positive(number):
    #         return max([number, 0.0])

    #     for record in self:
    #         previous_lines = record.reserve_id.line_ids.filtered(
    #             lambda l: l.sequence < record.sequence and \
    #             l.move_id.product_id == record.move_id.product_id and \
    #             l.move_id.location_id == record.move_id.location_id)

    #         to_add_qty = positive(record.reserved_uom_qty - positive(record.to_reserve_uom_qty))
            
    #         if not previous_lines:
    #             availability_uom_qty = record.move_id.availability_uom_qty
    #             to_substract_qty = 0.0
    #         else:
    #             availability_uom_qty = previous_lines[-1].availability_uom_qty
    #             to_substract_qty = positive(positive(previous_lines[-1].to_reserve_uom_qty) - previous_lines[-1].reserved_uom_qty)
    #             to_substract_qty = previous_lines[-1].move_id.product_uom._compute_quantity(to_substract_qty, record.move_id.product_uom)

    #         record.availability_uom_qty = availability_uom_qty + to_add_qty - to_substract_qty