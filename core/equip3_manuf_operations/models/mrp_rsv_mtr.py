from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import OrderedSet



class MrpRsvMtr(models.Model):
    _name = 'mrp.rsv.mtr'
    _description = 'MRP Reserve Material'

    sequence = fields.Integer()
    
    move_id = fields.Many2one('stock.move', string='Stock Move', required=True)
    product_id = fields.Many2one('product.product', string='Material', related='move_id.product_id')
    product_uom = fields.Many2one('uom.uom', related='move_id.product_uom', string='UoM')
    product_uom_qty = fields.Float(digits='Product Unit of Measure', related='move_id.product_uom_qty', string='To Consume')
    availability_uom_qty = fields.Float(digits='Product Unit of Measure', string='Available', compute='_compute_availability_uom')
    reserved_uom_qty = fields.Float(digits='Product Unit of Measure', related='move_id.reserved_availability', string='Reserved')
    to_reserve_uom_qty = fields.Float(digits='Product Unit of Measure', string='To Reserve')
    product_tracking = fields.Selection(string='Product Tracking', related="product_id.tracking", store=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', related='move_id.warehouse_id')
    location_id = fields.Many2one('stock.location', string='Location', related='move_id.location_id')
    production_id = fields.Many2one('mrp.production', string='Manufaturing Order', related='move_id.raw_material_production_id')
    workorder_id = fields.Many2one('mrp.workorder', string='Work Order', related='move_id.workorder_id')
    lot_ids = fields.Many2many(comodel_name='stock.production.lot', string='Lot/Serial Number', readonly=True)
    

    _sql_constraints = [
        ('unique_sequence', 'unique(production_id, sequence)', _('The sequence must be unique!'))
    ]

    @api.depends('move_id', 'production_id', 'sequence', 'reserved_uom_qty', 'to_reserve_uom_qty', 'production_id.mrp_rsv_mtr_ids', 'production_id.mrp_rsv_mtr_ids.sequence', 
    'production_id.mrp_rsv_mtr_ids.move_id', 'production_id.mrp_rsv_mtr_ids.to_reserve_uom_qty', 'production_id.mrp_rsv_mtr_ids.reserved_uom_qty', 'production_id.mrp_rsv_mtr_ids.availability_uom_qty')
    def _compute_availability_uom(self):

        def positive(number):
            return max([number, 0.0])

        for record in self:
            previous_lines = record.production_id.mrp_rsv_mtr_ids.filtered(
                lambda l: l.sequence < record.sequence and \
                l.move_id.product_id == record.move_id.product_id and \
                l.move_id.location_id == record.move_id.location_id)

            to_add_qty = positive(record.reserved_uom_qty - positive(record.to_reserve_uom_qty))
            
            if not previous_lines:
                availability_uom_qty = record.move_id.availability_uom_qty
                to_substract_qty = 0.0
            else:
                availability_uom_qty = previous_lines[-1].availability_uom_qty
                to_substract_qty = positive(positive(previous_lines[-1].to_reserve_uom_qty) - previous_lines[-1].reserved_uom_qty)
                to_substract_qty = previous_lines[-1].move_id.product_uom._compute_quantity(to_substract_qty, record.move_id.product_uom)

            record.availability_uom_qty = availability_uom_qty + to_add_qty - to_substract_qty

    def action_reserve_per_lot(self):
        return { 
                'type': 'ir.actions.act_window',
                'name': _('Partial Reserve Material'),
                'res_model': 'mrp.reserve.material.lot',
                'target': 'new',
                'view_mode': 'form',
                'context': {
                    'default_product_id': self.product_id.id,
                    'default_mrp_rsv_mtr_id':self.id,
                            }
            }