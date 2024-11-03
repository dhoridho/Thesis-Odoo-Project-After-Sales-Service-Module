# -*- coding: utf-8 -*-

import time
from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class InventoryAdjustment(models.Model):
	_inherit = 'stock.inventory'

	force_date = fields.Datetime(string="Force Date")

class StockPicking(models.Model):
	_inherit = 'stock.picking'

	force_date = fields.Datetime(string="Force Date")


class StockMove(models.Model):
	_inherit = 'stock.move'

	def _action_done(self, cancel_backorder=False):
		force_date = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
		if self.env.user.has_group('stock_force_date_app.group_stock_force_date'):
			for move in self:
				if move.picking_id:
					if move.picking_id.force_date:
						force_date = move.picking_id.force_date
					else:
						force_date = move.picking_id.date_done or fields.Datetime.now()
				if move.inventory_id:
					if move.inventory_id.force_date:
						force_date = move.inventory_id.force_date
					else:
						force_date = move.inventory_id.date

		res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
		if self.env.user.has_group('stock_force_date_app.group_stock_force_date'):
			if force_date:
				for move in res:
					move.write({'date':force_date})
					if move.move_line_ids:
						for move_line in move.move_line_ids:
							move_line.write({'date':force_date})
					if move.account_move_ids:
						for account_move in move.account_move_ids:
							if move.inventory_id:
								account_move.write({'ref':move.inventory_id.name})

					svl_ids = self.env['stock.valuation.layer'].search([('stock_move_id','in',res.ids)])
					if svl_ids and move.picking_id.force_date and move.picking_id.picking_type_code == 'incoming' and move.picking_id.group_id and not move.picking_id.group_id.sale_id:
						for svl in svl_ids:
							svl.write({'value': svl.quantity * move.price_unit, 'unit_cost': move.price_unit})
		return res


	def _create_account_move_line(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost):
		self.ensure_one()
		AccountMove = self.env['account.move'].with_context(default_journal_id=journal_id)

		if self.picking_id.group_id and not self.picking_id.group_id.sale_id and self.picking_id.force_date:
			cost = self.price_unit
		move_lines = self._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id, description)
		if move_lines:
			date = self._context.get('force_period_date', fields.Date.context_today(self))
			if self.env.user.has_group('stock_force_date_app.group_stock_force_date'):
				if self.picking_id.force_date:
					date = self.picking_id.force_date.date()
				if self.inventory_id.force_date:
					date = self.inventory_id.force_date.date()
			branch = False
			if self.picking_id.branch_id:
				branch = self.picking_id.branch_id.id
			if self.inventory_id.branch_id:
				branch = self.inventory_id.branch_id.id
			if branch:
				new_account_move = AccountMove.sudo().create({
					'journal_id': journal_id,
					'line_ids': move_lines,
					'date': date,
					'ref': description,
					'stock_move_id': self.id,
					'stock_valuation_layer_ids': [(6, None, [svl_id])],
					'move_type': 'entry',
					'branch_id': branch
				})
			else:
				new_account_move = AccountMove.sudo().create({
					'journal_id': journal_id,
					'line_ids': move_lines,
					'date': date,
					'ref': description,
					'stock_move_id': self.id,
					'stock_valuation_layer_ids': [(6, None, [svl_id])],
					'move_type': 'entry',
				})
			new_account_move._post()
