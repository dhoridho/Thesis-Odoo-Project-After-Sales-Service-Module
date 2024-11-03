from odoo import models, fields, api


class AgricultureCropEstate(models.Model):
    _name = 'crop.estate'
    _inherit = ['image.mixin']
    _description = 'Crop Estate Management'

    @api.depends('block_ids', 'block_ids.size')
    def _compute_area(self):
        for record in self:
            record.size = sum(record.block_ids.mapped('size'))

    name = fields.Char(string='Estate Name', required=True)
    location_id = fields.Many2one('stock.location', string='Location', required=True)
    size = fields.Float(string='Area', compute=_compute_area)
    uom_id = fields.Many2one('uom.uom', string='UOM', required=True)
    division_ids = fields.One2many('agriculture.division', 'estate_id', string='Divisions')
    block_ids = fields.One2many('crop.block', 'estate_id', string='Blocks')
