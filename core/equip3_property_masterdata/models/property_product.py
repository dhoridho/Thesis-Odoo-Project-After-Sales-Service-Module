from odoo import models, fields, api, _
from odoo.modules import get_module_resource
import base64
from odoo.exceptions import UserError


class PropertyProductTemplate(models.Model):
	_inherit = 'product.template'

	type = fields.Selection(selection_add=[('property', 'Property'),], ondelete={'property': 'cascade'})

	@api.model
	def _get_default_image_value(self, type):
		res = super(PropertyProductTemplate, self)._get_default_image_value(type)
		if type == 'property':
			image_path = get_module_resource('equip3_property_masterdata', 'static/src/img', 'property.png')
		return res

	@api.onchange('type')
	def _onchange_type_change_categ(self):
		res = super(PropertyProductTemplate, self)._onchange_type_change_categ()
		if self.type == 'property':
			product_category = self.env['product.category'].search([('stock_type', '=', 'property'),('name','=','Property')], limit=1)
			self.categ_id = product_category.id
			image_path = get_module_resource('equip3_property_masterdata', 'static/src/img', 'property.png')
			self.image_1920 = base64.b64encode(open(image_path, 'rb').read())
		return res


class PropertyProduct(models.Model):
	_inherit = 'product.product'
	
	base_price = fields.Float(string='Base Price')
	maintenance_spent = fields.Float(string='Maintenance Spent')
	parent_property = fields.Many2one('parent.property', string='Parent Property')
	property_owner_id = fields.Many2one('res.partner', string='Owner')
	daily_rent = fields.Float(string='Daily Rent')
	reasonable_rent_daily = fields.Boolean(string='Allow Discount In (%)')
	reasonable_percent_daily = fields.Float(string='Reasonable Price Percentage')
	property_pricelist_id = fields.Many2one(comodel_name='property.pricelist', string='Property Pricelist')

	@api.onchange('property_pricelist_id')
	def onchange_property_pricelist_id(self):
		if self.property_book_for and self.property_pricelist_id:
			self.rent_price = self.property_pricelist_id.yearly_price
			self.deposite = self.property_pricelist_id.monthly_price
			self.daily_rent = self.property_pricelist_id.daily_price

	@api.onchange('reasonable_percent','reasonable_rent','rent_price','reasonable_rent_daily','reasonable_percent_daily')
	def calculate_reasonable_rent(self):
		pass



	@api.model
	def default_get(self, fields):
		res = super(PropertyProduct, self).default_get(fields)
		context = dict(self.env.context) or {}
		if context.get('default_type') == 'property':
			product_category = self.env['product.category'].search([('stock_type', '=', 'property'),('name','=','Property')], limit=1)
			res.update({'categ_id': product_category.id})
		return res

	@api.onchange('type')
	def _onchange_type_change_categ(self):
		res = super(PropertyProduct, self)._onchange_type_change_categ()
		if self.type == 'property':
			image_path = get_module_resource('equip3_property_masterdata', 'static/src/img', 'property.png')
			self.image_1920 = base64.b64encode(open(image_path, 'rb').read())
		return res

	@api.model_create_multi
	def create(self, vals_list):
		res = super(PropertyProduct, self).create(vals_list)
		context = dict(self.env.context) or {}
		if context.get('default_type') == 'property':
			for rec in res:
					categ = vals_list[0].get('categ_id')
					rec.write({'categ_id': categ})
					rec.product_tmpl_id.write({'categ_id': categ})
		return res        


	def action_archive_property(self):
		return {
			'name': _('Confirmation'),
			'view_mode': 'form',
			'res_model': 'property.archive.wizard',
			'view_id': (self.env.ref('equip3_property_masterdata.property_archive_wizard_form').id, 'form'),
			'type': 'ir.actions.act_window',
			'target': 'new',
			'context': self.env.context,
		}

	def fields_view_get(self, view_id=None, view_type='tree', toolbar=False, submenu=False):
		res = super(PropertyProduct, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
		if view_type == 'tree':
			for button in res.get('toolbar', {}).get('action', []):
				# print("➡ button :", button.get('display_name'))
				if self._context.get('default_type') != 'property':
					if button.get('display_name') == 'Archive Property & Contract':
						res['toolbar']['action'].remove(button)
				else:
					if button.get('display_name') == 'Archive':
						res['toolbar']['action'].remove(button)
		return res