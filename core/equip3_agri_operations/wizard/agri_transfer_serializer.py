import json
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AgriTransferSerializer(models.TransientModel):
    _name = 'agri.transfer.serializer'
    _description = 'Agriculture Transfer Serializer'

    activity_record_id = fields.Many2one('agriculture.daily.activity.record', string='Plantation Record', required=True)
    line_ids = fields.One2many('agri.transfer.serializer.line', 'serialize_id', string='Lines')

    # technical fields
    next_no = fields.Integer(compute='_compute_next_no')
    next_crop_line_id = fields.Many2one('agriculture.crop.line', compute='_compute_next_crop_line')
    next_quantites = fields.Char()

    @api.depends('line_ids')
    def _compute_next_no(self):
        for record in self:
            record.next_no = len(record.line_ids) + 1

    @api.onchange('activity_record_id', 'line_ids')
    def _onchange_line_ids(self):
        crop_line_ids = self.activity_record_id.crop_line_ids
        line_ids = self.line_ids

        quantities = {}
        for crop_line in crop_line_ids:
            qty_left = crop_line.quantity - sum(line_ids.filtered(lambda o: o.crop_line_id == crop_line).mapped('product_uom_qty'))
            if crop_line.crop_id.crop.tracking == 'serial' and qty_left > 0:
                qty_left = 1
            quantities[crop_line.id] = qty_left

        self.next_quantites = json.dumps(quantities)

    @api.depends('activity_record_id', 'line_ids', 'line_ids.product_id', 'line_ids.product_uom_qty', 'line_ids.crop_line_id')
    def _compute_next_crop_line(self):
        for record in self:
            crop_line_ids = record.activity_record_id and record.activity_record_id.crop_line_ids or self.env['agriculture.crop.line']

            crop_line_qtys = {}
            for crop_line in crop_line_ids:
                if crop_line.id not in crop_line_qtys:
                    crop_line_qtys[crop_line.id] = crop_line.quantity
                else:
                    crop_line_qtys[crop_line.id] += crop_line.quantity

            for line in record.line_ids:
                crop_line_qtys[line.crop_line_id.id] -= line.product_uom_qty
            
            unfinished_crop_lines = [pid for pid, qty in crop_line_qtys.items() if qty > 0]
            record.next_crop_line_id = unfinished_crop_lines and unfinished_crop_lines[0] or False

    @api.constrains('line_ids')
    def _check_line_ids(self):
        for record in self:
            crop_line_ids = record.activity_record_id.crop_line_ids
            line_ids = record.line_ids
            for crop_line in crop_line_ids:
                crop_lines = line_ids.filtered(lambda o: o.crop_line_id == crop_line)
                if crop_line.quantity != sum(crop_lines.mapped('product_uom_qty')):
                    raise ValidationError(_('The quantity in lot/serial does not match the crop count quantity!'))
            
    @api.model
    def _prepare_serialize_values(self, activity_record):
        lines = []
        for no, crop_line in enumerate(activity_record.crop_line_ids):
            crop_id = crop_line.crop_id
            product_id = crop_id.crop
            product_tmpl_id = product_id.product_tmpl_id
            product_tracking = product_id.tracking
            product_uom_qty = product_tracking == 'lot' and crop_line.quantity or 1.0

            lines += [(0, 0, {
                'no': no + 1,
                'lot_id': crop_id.lot_id and crop_id.lot_id.id or False,
                'product_id': product_id.id,
                'product_uom_qty': product_uom_qty,
                'uom_id': crop_line.uom_id.id,
                'crop_line_id': crop_line.id
            })]
        return lines

    @api.model
    def default_get(self, fields):
        res = super(AgriTransferSerializer, self).default_get(fields)
        activity_record_id = res.get('activity_record_id', self.env.context.get('default_activity_record_id', False))
        if not activity_record_id:
            return res
        activity_record = self.env['agriculture.daily.activity.record'].browse(res.get('activity_record_id'))
        res['line_ids'] = self._prepare_serialize_values(activity_record)
        return res

    def action_confirm(self):
        self.ensure_one()
        line_ids = self.line_ids
        for crop_line in line_ids.mapped('crop_line_id'):
            data = []
            for line in line_ids.filtered(lambda o: o.crop_line_id == crop_line):
                data += [{
                    'lot_id': line.lot_id.id,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_uom_qty,
                    'uom_id': line.uom_id.id
                }]
            crop_line.lot_data = json.dumps({'data': data})
        return self.activity_record_id.with_context(skip_serializer=True).action_confirm()


class AgriTransferSerializerLine(models.TransientModel):
    _name = 'agri.transfer.serializer.line'
    _description = 'Agriculture Transfer Serializer Line'

    serialize_id = fields.Many2one('agri.transfer.serializer', required=True, ondelete='cascade')
    no = fields.Integer()
    lot_id = fields.Many2one('stock.production.lot', string='Lot/Serial Number', required=True)
    product_id = fields.Many2one('product.product', string='Crop', required=True)
    product_uom_qty = fields.Float(digits='Product Unit of Measure', string='Quantity')
    uom_id = fields.Many2one('uom.uom', string='UoM', required=True)
    crop_line_id = fields.Many2one('agriculture.crop.line', required=True)
    crop_lot_id = fields.Many2one('stock.production.lot', related='crop_line_id.crop_id.lot_id')

    @api.onchange('crop_line_id')
    def _onchange_crop_line_id(self):
        self.product_id = self.crop_line_id and self.crop_line_id.crop_id.crop.id or False
        self.uom_id = self.crop_line_id and self.crop_line_id.uom_id.id or False

        next_quantities = json.loads(self.serialize_id.next_quantites)
        self.product_uom_qty = next_quantities.get(str(self.crop_line_id.id), 0.0)
