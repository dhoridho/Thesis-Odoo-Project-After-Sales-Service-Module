from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
class ProductTemplate(models.Model):
    _inherit = "product.template"

    asset_parts_line = fields.One2many(comodel_name='asset.parts.line', inverse_name='asset_part_id', string='Asset Parts Line')
    asset_control_category = fields.Many2one(comodel_name='maintenance.equipment.category', string='Asset Control Category')        

class AssetPartsLine(models.Model):
    _name = "asset.parts.line"
    _description = "Asset Parts Line"

    asset_part_id = fields.Many2one(comodel_name='product.template', string='Asset Part')
    name = fields.Char(string='Parts')
    qty = fields.Integer(string='Quantity')
