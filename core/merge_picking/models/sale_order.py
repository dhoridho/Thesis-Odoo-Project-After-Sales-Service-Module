# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import time
from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError, RedirectWarning, ValidationError, Warning

class SaleOrder(models.Model):
	_inherit = "sale.order"

	merged = fields.Boolean(string='Merged')

	# @api.depends('procurement_group_id')
	# def _compute_picking_ids(self):
	# 	for order in self:
	# 		order.picking_ids = self.env['stock.picking'].search([('group_id', '=', order.procurement_group_id.id)]) if order.procurement_group_id else []
	# 		order.delivery_count = len(order.picking_ids)
	# 	for order in self:
	# 		if order.merged:
	# 			for a in self.env['stock.picking'].search([]):
	# 				if a.sale_ids:
	# 					for b in a.sale_ids:
	# 						if order.id == b.id:
	# 							order.picking_ids = [(4, a.id)]
	# 	for order in self:
	# 		order.delivery_count = len(order.picking_ids)
			
			

	# picking_ids = fields.Many2many('stock.picking', compute='_compute_picking_ids', string='Picking associated to this sale')
	# delivery_count = fields.Integer(string='Delivery Orders', compute='_compute_picking_ids')
	

			
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
