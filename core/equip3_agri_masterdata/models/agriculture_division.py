from odoo import models, fields, api


class AgricultureDivision(models.Model):
    _name = 'agriculture.division'
    _inherit = ['image.mixin']
    _description = 'Agriculture Division'

    @api.depends('block_ids', 'block_ids.size')
    def _compute_area(self):
        for record in self:
            record.area = sum(record.block_ids.mapped('size'))

    name = fields.Char(required=True, copy=False, string='Division Name')
    estate_id = fields.Many2one('crop.estate', string='Estate', required=True)
    area = fields.Float(string='Area', digits='Product Unit of Measure', compute=_compute_area)
    area_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    block_ids = fields.One2many('crop.block', 'division_id', string='Blocks', readonly=True)
