# -*- coding: utf-8 -*-

from itertools import groupby
from datetime import datetime, timedelta

from odoo.http import request
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang
from odoo.tools import html2plaintext
import odoo.addons.decimal_precision as dp
import operator

class main_hide(models.Model):
	_name = "multi.main.hide"

	company_id = fields.Many2one('res.company')

	ui_menu_id = fields.Many2one('ir.ui.menu',string = "Menu Name")
	user_id = fields.Many2many("res.users",string = "Users",required = True)

class _inherit_company(models.Model):
	_inherit = "res.company"

	main_hide_ids = fields.One2many("multi.main.hide",'company_id',string = "Hide Manu")

class hide_menu_group(models.Model):
	_inherit = 'ir.ui.menu'

	@api.model
	@api.returns('self')
	def get_menus_users(self):
		user_list =[]
		dropdown_compnay_id = request.httprequest.cookies.get('cids') or ''
		current_company = self.env.user.company_id
		if dropdown_compnay_id:
			current_company = self.env['res.company'].browse(dropdown_compnay_id)			
		user_company = self.env['res.company'].search([('id','=',current_company.id)])
		if self.env.user.has_group('show_hide_menu_multi_company_app.group_hide_menu'):
			if user_company.main_hide_ids:
				user_list.append(user_company.main_hide_ids)
			return user_list

	@api.model
	def load_menus(self, debug):
		
		main_list = []
		lat_list = []
		sub_menu = []
		menu_sub_roots = []
		fields = ['name', 'sequence', 'parent_id', 'action', 'web_icon',  'web_icon_data']

		menu_roots = self.get_user_roots()
		menu_roots_ids = self.get_user_roots()
		for i in menu_roots_ids:
			main_list.append(i.id)

		current_users =self.env.user
		
		menu_ro = self.get_menus_users()
		
		if menu_ro:
			for i in menu_ro:
				for menus in i:
					for u_ids in menus.user_id:
						if u_ids == current_users:
							lat_list.append(menus.ui_menu_id.id)
							menu_sub_roots = set(main_list) - set(lat_list)
							menu_roots = self.search([('id','in', list(menu_sub_roots)),('parent_id', '=', False)])

		menu_roots_data = menu_roots.read(fields) if menu_roots else []
		menu_root = {
			'id': False,
			'name': 'root',
			'parent_id': [-1, ''],
			'children': menu_roots_data,
			'all_menu_ids': menu_roots.ids,
		}

		if not menu_roots:
			return menu_root

		menus = self.search([('id', 'child_of', menu_roots.ids)])

		a = set(menus.ids) - set(lat_list)
		menus = self.search([('id', 'in', list(a))])
		menu_items = menus.read(fields)

		menu_items.extend(menu_roots_data)
		menu_root['all_menu_ids'] = menus.ids

		menu_items_map = {menu_item["id"]: menu_item for menu_item in menu_items}
		for menu_item in menu_items:
			parent = menu_item['parent_id'] and menu_item['parent_id'][0]
			if parent in menu_items_map:
				menu_items_map[parent].setdefault(
					'children', []).append(menu_item)

		for menu_item in menu_items:
			menu_item.setdefault('children',  []).sort(key=operator.itemgetter('sequence'))

		(menu_roots + menus)._set_menuitems_xmlids(menu_root)

		return menu_root