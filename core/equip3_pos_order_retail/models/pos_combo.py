from odoo import api, fields, models, _

class ComboOption(models.Model):
	_name = 'combo.option'
	_inherit = ['image.mixin']
	_rec_name = 'combo_name'
	_description = 'combo_name'

	combo_name = fields.Char(string="Combo Option", required=True)
	item_ids = fields.One2many('combo.option.item', 'combo_option_id', string="Items")

class ComboOptionItem(models.Model):
	_name = 'combo.option.item'

	combo_option_id = fields.Many2one('combo.option', string="Combo Option")
	product_id = fields.Many2one('product.template', string="Product", required=True)
	product_variant_id = fields.Many2one('product.product', related="product_id.product_variant_id", store=True)
	extra_price = fields.Float(string="Extra Price")


class ProductTemplate(models.Model):
	_inherit = 'product.template'

	is_combo_product = fields.Boolean(string="Combo Product")
	combo_option_id = fields.Many2one('combo.option', string="Combo Option")
	combo_option_items = fields.One2many('combo.option.item', related="combo_option_id.item_ids", string="Combo Option Items", readonly=True)