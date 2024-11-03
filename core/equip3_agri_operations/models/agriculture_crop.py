from odoo import models, fields, api, _


class AgricultureCrop(models.Model):
    _inherit = 'agriculture.crop'

    def name_get(self):
        result = []
        for record in self:
            name = '%s - %s - %s - %s' % (record.crop.display_name, record.lot_id.display_name, record.crop_count, record.uom_id.display_name)
            result.append((record.id, name))
        return result

    history_ids = fields.One2many('agriculture.crop.history', 'crop_id', string='History', readonly=True)
    lot_id = fields.Many2one('stock.production.lot', string='Lot/Serial Number')
    move_line_id = fields.Many2one('stock.move.line', string='Planting Move Line')
    product_qty = fields.Float(compute='_compute_product_qty')

    @api.depends('uom_id', 'crop', 'crop_count')
    def _compute_product_qty(self):
        for record in self:
            uom_id = record.uom_id
            product_id = record.crop
            product_uom_qty = record.crop_count
            product_qty  = 0.0
            if uom_id and product_id and product_id.uom_id:
                product_qty = uom_id._compute_quantity(product_uom_qty, product_id.uom_id)
            record.product_qty = product_qty


class AgricultureCropHistory(models.Model):
    _name = 'agriculture.crop.history'
    _description = 'Agriculture Crop History'

    crop_id = fields.Many2one('agriculture.crop', string='Crop', required=True, ondelete='cascade')
    activity_plan_id = fields.Many2one('agriculture.daily.activity', string='Nursery Plan')
    activity_line_id = fields.Many2one('agriculture.daily.activity.line', string='Nursery Lines', required=True)
    activity_record_id = fields.Many2one('agriculture.daily.activity.record', string='Nursery Record', required=True)
    activity_id = fields.Many2one('crop.activity', string='Activity', required=True)
    previous_qty = fields.Float(string='Previous')
    adjusted_qty = fields.Float(string='Adjusted')
