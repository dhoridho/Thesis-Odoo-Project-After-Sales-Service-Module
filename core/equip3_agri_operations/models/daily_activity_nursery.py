import json
from odoo import models, fields, api, _


class PlantationNursery(models.Model):
    _name = 'agriculture.daily.activity.nursery'
    _description = 'Plantation Nursery'

    @api.depends('daily_activity_id', 'daily_activity_id.line_ids')
    def _compute_allowed_activity_lines(self):
        for record in self:
            line_ids = []
            if record.daily_activity_id:
                line_ids = record.daily_activity_id.line_ids.ids
            record.allowed_activity_line_ids = [(6, 0, line_ids)]

    activity_line_sequence = fields.Integer()
    allowed_activity_line_ids = fields.Many2many('agriculture.daily.activity.line', compute=_compute_allowed_activity_lines)

    daily_activity_id = fields.Many2one('agriculture.daily.activity', string='Plantation Plan')
    activity_line_id = fields.Many2one('agriculture.daily.activity.line', string='Plantation Lines')
    activity_record_id = fields.Many2one('agriculture.daily.activity.record', string='Plantation Record')

    product_id = fields.Many2one('product.product', string='Product', required=True, domain="[('is_agriculture_product', '=', True)]")
    block_id = fields.Many2one('crop.block', string='Block', required=True)
    count = fields.Float(string='Crop Count', default=1.0)
    date = fields.Date(string='Crop Date', required=True)
    uom_id = fields.Many2one('uom.uom', string='UOM', required=True)
    original_move = fields.Boolean(copy=False)
    stock_move_id = fields.Many2one('stock.move', string='Stock Move')

    lot_data = fields.Text()

    crop_id = fields.Many2one('agriculture.crop', string='Crop', required=True)
    lot_id = fields.Many2one('stock.production.lot', string='Lot/Serial Number')
    current_qty = fields.Float(string='Current Quantity', digits='Product Unit of Measure')

    product_qty = fields.Float(compute='_compute_product_qty')

    @api.depends('uom_id', 'product_id', 'count')
    def _compute_product_qty(self):
        for record in self:
            uom_id = record.uom_id
            product_id = record.product_id
            product_uom_qty = record.count
            product_qty = 0.0
            if uom_id and product_id and product_id.uom_id:
                product_qty = uom_id._compute_quantity(product_uom_qty, product_id.uom_id)
            record.product_qty = product_qty

    @api.onchange('crop_id')
    def _onchange_crop_id(self):
        crop = self.crop_id
        self.product_id = crop and crop.crop.id or False
        self.lot_id = crop and crop.lot_id.id or False
        self.current_qty = crop and crop.crop_count or 0.0
        self.count = crop and crop.crop_count or 0.0

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id

    def _prepare_moves_values(self):
        self.ensure_one()
        activity_record_id = self.activity_record_id
        activity_line_id = activity_record_id.activity_line_id
        activity_plan_id = activity_line_id.daily_activity_id

        company_id = activity_record_id.company_id
        branch_id = activity_record_id.branch_id

        block_location = self.block_id.location_id
        production_location = self.product_id.with_company(company_id).property_stock_production
        reference = self.activity_record_id.name

        values = {
            'name': reference,
            'origin': reference,
            'product_id': self.product_id.id,
            'product_uom': self.uom_id.id,
            'date': fields.Date.today(),
            'product_uom_qty': self.count,
            'quantity_done': self.count,
            'location_id': production_location.id,
            'location_dest_id': block_location.id,
            'activity_record_planting_id': activity_record_id.id,
            'activity_line_planting_id': activity_line_id.id,
            'activity_plan_planting_id': activity_plan_id.id,
            'nursery_id': self.id,
            'company_id': company_id.id,
            'branch_id': branch_id.id
        }

        if self.lot_data:
            lot_data = json.loads(self.lot_data)['data']
            
            move_line_values = []
            for line in lot_data:
                lot_id = self.env['stock.production.lot'].create({
                    'name': line['lot_name'],
                    'product_id': line['product_id'],
                    'company_id': company_id.id,
                    'ref': reference
                })
                move_line_values += [(0, 0, {
                    'product_id': line['product_id'],
                    'product_uom_id': line['uom_id'],
                    'qty_done': line['product_uom_qty'],
                    'lot_id': lot_id.id,
                    'location_id': production_location.id,
                    'location_dest_id': block_location.id,
                    'company_id': company_id.id
                })]

            values.update({'move_line_ids': move_line_values})
        return values
