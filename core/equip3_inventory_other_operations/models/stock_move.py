from odoo import models, fields
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, OrderedSet
from datetime import datetime, date

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    is_from_repair_order = fields.Boolean(related="picking_id.is_from_repair_order")


class StockMove(models.Model):
    _inherit = "stock.move"

    def _action_done(self, cancel_backorder=False):
        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
        context = dict(self._context) or {}
        if context.get('end_repair'):
            stock_valuation_layer_ids = self.repair_create_out_svl()
            repair_id = self.env['repair.order'].browse(self.env.context.get('repair_id'))
            if repair_id.operations.filtered(lambda r: r.type == 'add'):
                move_line_data = []
                debit_vals = {
                    'name': repair_id.product_id.name,
                    'product_id': repair_id.product_id.id,
                    'quantity': repair_id.product_qty,
                    'product_uom_id': repair_id.product_id.uom_id.id,
                    'ref': repair_id.name,
                    'account_id': repair_id.product_id.categ_id.property_stock_valuation_account_id.id,
                }
                debit = 0
                for line in repair_id.operations.filtered(lambda r: r.type == 'add'):
                    stock_valuation_layer_id = line.move_id.stock_valuation_layer_ids
                    for svl in stock_valuation_layer_id:
                        debit += abs(svl.value)
                        credit_vals = {
                            'name': svl.description,
                            'product_id': svl.stock_move_id.product_id.id,
                            'quantity': svl.quantity,
                            'product_uom_id': svl.product_id.uom_id.id,
                            'ref': repair_id.name,
                            'credit': abs(svl.value),
                            'debit': 0,
                            'account_id': svl.stock_move_id.product_id.categ_id.property_stock_account_output_categ_id.id,
                        }
                        move_line_data.append((0, 0, credit_vals))
                debit_vals.update({
                    'debit': debit,
                })
                move_line_data.append((0, 0, debit_vals))
                new_account_move = self.env['account.move'].create({
                    'journal_id': repair_id.product_id.categ_id.property_stock_journal.id,
                    'line_ids': move_line_data,
                    'date': date.today(),
                    'ref': repair_id.name,
                    'repair_id': repair_id.id,
                    'move_type': 'entry',
                })
                new_account_move._post()
            if repair_id.operations.filtered(lambda r: r.type == 'remove'):
                move_line_data = []
                credit_vals = {
                    'name': repair_id.product_id.name,
                    'product_id': repair_id.product_id.id,
                    'quantity': repair_id.product_qty,
                    'product_uom_id': repair_id.product_id.uom_id.id,
                    'ref': repair_id.name,
                    'account_id': repair_id.product_id.categ_id.property_stock_valuation_account_id.id,
                }
                credit = 0
                for line in repair_id.operations.filtered(lambda r: r.type == 'remove'):
                    stock_valuation_layer_id = line.move_id.stock_valuation_layer_ids
                    debit_vals = {
                        'name': line.name,
                        'product_id': line.product_id.id,
                        'quantity': line.product_uom_qty,
                        'product_uom_id': line.product_id.uom_id.id,
                        'ref': repair_id.name,
                        'debit': abs(line.product_id.standard_price * line.product_uom_qty),
                        'credit': 0,
                        'account_id': line.product_id.categ_id.property_stock_account_output_categ_id.id,
                    }
                    credit += abs(debit_vals['debit'])
                    move_line_data.append((0, 0, debit_vals))
                credit_vals.update({
                    'credit': credit,
                })
                move_line_data.append((0, 0, credit_vals))
                new_account_move = self.env['account.move'].create({
                    'journal_id': repair_id.product_id.categ_id.property_stock_journal.id,
                    'line_ids': move_line_data,
                    'date': date.today(),
                    'ref': repair_id.name,
                    'move_type': 'entry',
                    'repair_id': repair_id.id,
                })
                new_account_move._post()
        return res

    def _create_out_svl(self, forced_quantity=None):
        context = dict(self._context) or {}
        if context.get('end_repair'):
            return self.env['stock.valuation.layer']
        else:
            return super(StockMove, self)._create_out_svl(forced_quantity=forced_quantity)

    def repair_create_out_svl(self, forced_quantity=None):
        svl_vals_list = []
        for move in self:
            move = move.with_company(move.company_id)
            valued_move_lines = move._get_out_move_lines()
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)
            if float_is_zero(forced_quantity or valued_quantity, precision_rounding=move.product_id.uom_id.rounding):
                continue
            svl_vals = move.product_id._prepare_out_svl_vals(forced_quantity or valued_quantity, move.company_id)
            svl_vals.update(move._prepare_common_svl_vals())
            if forced_quantity:
                svl_vals['description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
            svl_vals['description'] += svl_vals.pop('rounding_adjustment', '')
            svl_vals_list.append(svl_vals)
        return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)
