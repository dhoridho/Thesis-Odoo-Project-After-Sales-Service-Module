from odoo import api, fields, models


class MPTiktokProductAttribute(models.Model):
    _name = 'mp.tiktok.product.attribute'
    _inherit = 'mp.base'
    _description = 'Marketplace Tiktok Attribute'

    name = fields.Char(string='Attribute Name')
    value_ids = fields.One2many('mp.tiktok.product.attribute.values', 'attribute_id', string='Values')
    mp_product_id = fields.Many2one('mp.product', string='Product ID', ondelete='cascade')
    category_id = fields.Many2one(comodel_name='mp.tiktok.product.category', string='Tiktok Category', required=False)


class MPTiktokProductAttributeValues(models.Model):
    _name = 'mp.tiktok.product.attribute.values'
    _description = 'Marketplace Tiktok Attribute Values'

    name = fields.Char(string='Attribute Value')
    value_id = fields.Char(string='Attribute Value ID')
    attribute_id = fields.Many2one('mp.tiktok.product.attribute', string='Product ID', ondelete='cascade')
    # category_id = fields.Many2one(comodel_name="mp.tiktok.product.category", string="Tiktok Category", required=False)


class MPTiktokProductAttributeLine(models.Model):
    _name = 'mp.tiktok.product.attribute.line'
    _description = 'Marketplace Tiktok Attribute line'

    attribute_id = fields.Many2one('mp.tiktok.product.attribute', string='Tiktok Attribute', readonly=True)
    attribute_value_id = fields.Many2one('mp.tiktok.product.attribute.values', string='Value')
    category_id = fields.Many2one('mp.tiktok.product.category', string='Tiktok Category ID')
    tts_product_id = fields.Many2one('mp.product', string='Tiktok Product ID')
    product_tmpl_id = fields.Many2one('product.template', string='Tiktok Product Template')
