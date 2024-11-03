import json
from odoo import models, fields, api, _


class AgriMoveSerializer(models.TransientModel):
    _name = 'agri.move.serializer'
    _description = 'Move Serializer'

    move_id = fields.Many2one('stock.move', required=True)
    product_id = fields.Many2one('product.product', related='move_id.product_id')
    product_tracking = fields.Selection(related='product_id.tracking')

    to_serialize_qty = fields.Float(digits='Product Unit of Measure', string='To Serialize')
    per_lot_qty = fields.Float(digits='Product Unit of Measure', string='Quantity per Lot', default=1.0)
    line_ids = fields.One2many('agri.move.serializer.line', 'serializer_id', string='Lines')

    # technicak fields
    next_sequence = fields.Integer(compute='_compute_next_sequence')
    default_quantity = fields.Float(compute='_compute_default_quantity')

    def default_get(self, field_list):
        res = super(AgriMoveSerializer, self).default_get(field_list)
        move_id = self.env.context.get('default_move_id', res.get('move_id', False))
        if move_id:
            move = self.env['stock.move'].browse(move_id)
            if move.harvest_serialize_data:
                data = json.loads(move.harvest_serialize_data)
                res.update({
                    'to_serialize_qty': data['to_serialize_qty'],
                    'per_lot_qty': data['per_lot_qty'],
                    'line_ids': [(0, 0, line_values) for line_values in data['line_ids']]
                })
            else:
                res.update({
                    'to_serialize_qty': move.product_uom_qty,
                    'per_lot_qty': 1.0 if move.agri_product_tracking == 'serial' else move.product_uom_qty
                })
        return res

    def action_assign(self):
        self.ensure_one()
        product_id = self.product_id
        product_tmpl_id = product_id.product_tmpl_id
        product_tracking = self.product_tracking
        quantity = self.per_lot_qty
        qty_left = self.to_serialize_qty

        is_autogenerate = product_id._is_agri_auto_generate()
        sequence = int(product_id.in_current_sequence if product_tracking == 'lot' else product_id.current_sequence)

        product_sequence = {}
        lot_names = []

        arange = self.to_serialize_qty // quantity
        if self.to_serialize_qty % quantity > 0:
            arange += 1

        line_values = [(5,)]
        for sequence in range(int(arange)):
            if is_autogenerate:
                current_sequence = product_sequence.get(product_id.id, sequence)
                while True:
                    lot_name = product_tmpl_id._get_next_lot_and_serial(current_sequence=current_sequence)
                    if not self.env['stock.production.lot'].search([('name', '=', lot_name)]) and lot_name not in lot_names:
                        lot_names += [lot_name]
                        break
                    current_sequence += 1
                product_sequence[product_id.id] = current_sequence
            else:
                lot_name = self.env['ir.sequence'].next_by_code('stock.lot.serial')

            taken_qty = min([quantity, qty_left])
            line_values += [(0, 0, {
                'sequence': sequence + 1,
                'product_id': product_id.id,
                'lot_name': lot_name,
                'quantity': taken_qty
            })]

            qty_left -= taken_qty
        
        self.line_ids = line_values

        if self.env.context.get('pop_back', False):
            return {
                'name': _('Lot/Serial Number'),
                'type': 'ir.actions.act_window',
                'res_model': 'agri.move.serializer',
                'target': 'new',
                'view_mode': 'form',
                'context': self.env.context,
                'res_id': self.id
            }

    def action_confirm(self):
        self.ensure_one()
        data = json.dumps({
            'to_serialize_qty': self.to_serialize_qty,
            'per_lot_qty': self.per_lot_qty,
            'line_ids': [{
                'sequence': line.sequence,
                'product_id': line.product_id.id,
                'lot_name': line.lot_name,
                'quantity': line.quantity
            } for line in self.line_ids]
        })
        self.move_id.write({'harvest_serialize_data': data})

    @api.depends('line_ids')
    def _compute_next_sequence(self):
        for record in self:
            record.next_sequence = len(record.line_ids) + 1

    @api.depends('product_tracking')
    def _compute_default_quantity(self):
        for record in self:
            default = 1.0
            if record.product_tracking == 'lot':
                default = record.per_lot_qty
            record.default_quantity = default


class AgriMoveSerializerLine(models.TransientModel):
    _name = 'agri.move.serializer.line'
    _description = 'Move Serializer Line'

    serializer_id = fields.Many2one('agri.move.serializer', required=True, ondelete='cascade')
    sequence = fields.Integer(string='No.', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True, required=True)
    lot_name = fields.Char(string='Lot/Serial Number', required=True)
    quantity = fields.Float(digits='Product Unit of Measure')
