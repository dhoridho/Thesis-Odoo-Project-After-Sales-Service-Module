import json
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AgriSerializer(models.TransientModel):
    _name = 'agri.serializer'
    _description = 'Agriculture Serializer'

    activity_record_id = fields.Many2one('agriculture.daily.activity.record', string='Plantation Record', required=True)
    line_ids = fields.One2many('agri.serializer.line', 'serialize_id', string='Lines')

    # technical fields
    next_no = fields.Integer(compute='_compute_next_no')
    next_nursery_id = fields.Many2one('agriculture.daily.activity.nursery', compute='_compute_next_nursery')
    next_quantites = fields.Char()
    next_lot_sequence = fields.Char()

    @api.depends('line_ids')
    def _compute_next_no(self):
        for record in self:
            record.next_no = len(record.line_ids) + 1

    @api.onchange('activity_record_id', 'line_ids')
    def _onchange_line_ids(self):
        nursery_ids = self.activity_record_id.nursery_ids
        line_ids = self.line_ids

        quantities = {}
        for nursery in nursery_ids:
            qty_left = nursery.count - sum(line_ids.filtered(lambda o: o.nursery_id == nursery).mapped('product_uom_qty'))
            if nursery.product_id.tracking == 'serial' and qty_left > 0:
                qty_left = 1
            quantities[nursery.id] = qty_left

        sequences = {}
        for product in nursery_ids.mapped('product_id').filtered(lambda p: p._is_agri_auto_generate()):
            product_lines = line_ids.filtered(lambda o: o.product_id == product)
            sequences[product.id] = product_lines and max(product_lines.mapped('lot_sequence')) + 1 or 1

        self.next_quantites = json.dumps(quantities)
        self.next_lot_sequence = json.dumps(sequences)

    @api.depends('activity_record_id', 'line_ids', 'line_ids.product_id', 'line_ids.product_uom_qty', 'line_ids.product_id.nursery_id')
    def _compute_next_nursery(self):
        for record in self:
            nursery_ids = record.activity_record_id and record.activity_record_id.nursery_ids or self.env['agriculture.daily.activity.nursery']

            nursery_qtys = {}
            for nursery in nursery_ids:
                if nursery.id not in nursery_qtys:
                    nursery_qtys[nursery.id] = nursery.count
                else:
                    nursery_qtys[nursery.id] += nursery.count

            for line in record.line_ids:
                nursery_qtys[line.nursery_id.id] -= line.product_uom_qty
            
            unfinished_nurseries = [pid for pid, qty in nursery_qtys.items() if qty > 0]
            record.next_nursery_id = unfinished_nurseries and unfinished_nurseries[0] or False

    @api.constrains('line_ids')
    def _check_line_ids(self):
        for record in self:
            nursery_ids = record.activity_record_id.nursery_ids
            line_ids = record.line_ids
            for nursery in nursery_ids:
                nursery_lines = line_ids.filtered(lambda o: o.nursery_id == nursery)
                if nursery.count != sum(nursery_lines.mapped('product_uom_qty')):
                    raise ValidationError(_('The quantity in lot/serial does not match the crop count quantity!'))
            
    @api.model
    def _prepare_serialize_values(self, activity_record):
        no = 1
        lines = []
        product_sequence = {}
        lot_names = []
        for nursery in activity_record.nursery_ids:
            uom_id = nursery.uom_id
            product_id = nursery.product_id
            product_tmpl_id = product_id.product_tmpl_id
            product_tracking = product_id.tracking
            product_uom_qty = product_tracking == 'lot' and nursery.count or 1.0

            is_autogenerate = product_id._is_agri_auto_generate()
            sequence = int(product_tracking == 'lot' and product_id.in_current_sequence or product_id.current_sequence)
            digits = product_tracking == 'lot' and product_id.in_digits or product_id.digits

            for i in range(product_tracking == 'lot' and 1 or int(nursery.count)):
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
                    current_sequence = -1
                    lot_name = self.env['ir.sequence'].next_by_code('stock.lot.serial')

                lines += [(0, 0, {
                    'no': no,
                    'lot_name': lot_name,
                    'product_id': product_id.id,
                    'product_uom_qty': product_uom_qty,
                    'uom_id': uom_id.id,
                    'nursery_id': nursery.id,
                    'lot_sequence': current_sequence
                })]

                no +=1
        return lines

    @api.model
    def default_get(self, fields):
        res = super(AgriSerializer, self).default_get(fields)
        activity_record_id = res.get('activity_record_id', self.env.context.get('default_activity_record_id', False))
        if not activity_record_id:
            return res
        activity_record = self.env['agriculture.daily.activity.record'].browse(res.get('activity_record_id'))
        res['line_ids'] = self._prepare_serialize_values(activity_record)
        return res

    def action_confirm(self):
        self.ensure_one()
        line_ids = self.line_ids
        for nursery in line_ids.mapped('nursery_id'):
            nursery.lot_data = json.dumps({
                'data': [{
                    'lot_name': line.lot_name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_uom_qty,
                    'uom_id': line.uom_id.id
                } for line in line_ids.filtered(lambda o: o.nursery_id == nursery)]
            })

        for product in line_ids.mapped('product_id').filtered(lambda p: p._is_agri_auto_generate()):
            seq_to_update = product.tracking == 'lot' and 'in_current_sequence' or 'current_sequence'
            digits = product.tracking == 'lot' and 'in_digits' or 'digits'
            next_sequence = json.loads(self.next_lot_sequence).get(str(product.id), 1)
            product.write({seq_to_update: str(next_sequence).zfill(product[digits])})
        
        return self.activity_record_id.with_context(skip_serializer=True).action_confirm()


class AgriSerializerLine(models.TransientModel):
    _name = 'agri.serializer.line'
    _description = 'Agriculture Serializer Line'

    serialize_id = fields.Many2one('agri.serializer', required=True, ondelete='cascade')
    no = fields.Integer()
    lot_name = fields.Char(string='Lot/Serial Number', required=True)
    product_id = fields.Many2one('product.product', string='Crop', required=True)
    product_uom_qty = fields.Float(digits='Product Unit of Measure', string='Quantity')
    uom_id = fields.Many2one('uom.uom', string='UoM', required=True)
    nursery_id = fields.Many2one('agriculture.daily.activity.nursery', required=True)

    # technical fields
    product_tracking = fields.Selection(related='product_id.tracking')
    is_autogenerate = fields.Boolean(compute='_compute_is_autogenerate')
    lot_sequence = fields.Integer(default=-1)

    @api.depends('product_id')
    def _compute_is_autogenerate(self):
        for record in self:
            product_id = record.product_id
            record.is_autogenerate = product_id and product_id._is_agri_auto_generate() or False

    @api.onchange('nursery_id')
    def _onchange_nursery_id(self):
        self.product_id = self.nursery_id and self.nursery_id.product_id.id or False
        self.uom_id = self.nursery_id and self.nursery_id.uom_id.id or False

        next_quantities = json.loads(self.serialize_id.next_quantites)
        self.product_uom_qty = next_quantities.get(str(self.nursery_id.id), 0.0)

        if self.product_id and self.product_id._is_agri_auto_generate():
            next_sequences = json.loads(self.serialize_id.next_lot_sequence)
            next_sequence = next_sequences.get(str(self.product_id.id), 0)
            self.lot_name = self.product_id.product_tmpl_id._get_next_lot_and_serial(current_sequence=next_sequence)
            self.lot_sequence = next_sequence
