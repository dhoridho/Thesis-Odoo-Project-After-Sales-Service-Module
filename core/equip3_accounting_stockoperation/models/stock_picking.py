from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import logging
from datetime import datetime, date, timedelta

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        res = super(StockPicking, self)._action_done()        
        if self.move_line_ids.filtered(lambda r: r.product_id.type in ('consu', 'service')):
            date_today = str(date.today())
            PurchaseOrder = self.env['purchase.order'].search([('name', '=', self.group_id.name)]) 
            # .filtered(lambda tax: tax.company_id == self.line_id.company_id)\
            if len(PurchaseOrder) > 0:
                ICP = self.env['ir.config_parameter'].sudo()
                is_product_service_operation = ICP.get_param('is_product_service_operation', False)
                for move_line in self.move_line_ids:
                    line_ids_det = []
                    if move_line.product_id.categ_id.property_valuation == 'real_time' and move_line.product_id.type in ['consu','service']:
                        if move_line.product_id.type == 'service':
                            if not is_product_service_operation:
                                continue
                        orderline = PurchaseOrder.order_line
                        lines = self.env['purchase.order.line'].search([('id', 'in', orderline.ids)])
                        for line in orderline:
                            line_ids_det = []
                            if line.product_id == move_line.product_id:
                                price_unit = line.price_unit
                                price_unit = price_unit * move_line.qty_done
                                amount_currency = price_unit
                                balance = PurchaseOrder.currency_id._convert(amount_currency, PurchaseOrder.company_id.currency_id, PurchaseOrder.company_id, date_today)
                                line1 = {
                                        'date': date_today,
                                        'name': self.name + " " + move_line.product_id.name + " " + date_today,
                                        'account_id': move_line.product_id.categ_id.property_stock_valuation_account_id.id,
                                        'currency_id': PurchaseOrder.currency_id.id,
                                        'debit': balance > 0.0 and balance or 0.0,
                                        'credit': balance < 0.0 and -balance or 0.0,                            
                                        }
                                
                                if line1['credit'] > 0:
                                    line1['amount_currency'] = -amount_currency
                                else:
                                    line1['amount_currency'] = amount_currency
                                
                                line_ids_det.append((0, 0, line1))

                                line2 = {
                                        'date': date_today,
                                        'name': self.name + " " + move_line.product_id.name + " " + date_today,
                                        'account_id': move_line.product_id.categ_id.property_stock_account_input_categ_id.id,
                                        'currency_id': PurchaseOrder.currency_id.id,
                                        'debit': balance < 0.0 and -balance or 0.0,
                                        'credit': balance > 0.0 and balance or 0.0,
                                        }
                                
                                if line2['credit'] > 0:
                                    line2['amount_currency'] = -amount_currency
                                else:
                                    line2['amount_currency'] = amount_currency

                                line_ids_det.append((0, 0, line2))
                                
                                if line_ids_det:
                                    all_move_vals = {
                                                        'date': date_today,
                                                        'ref': self.name + " " + move_line.product_id.name,
                                                        'journal_id': move_line.product_id.categ_id.property_stock_journal.id,
                                                        'currency_id': PurchaseOrder.currency_id.id,
                                                        'line_ids': line_ids_det
                                                    }
                                    AccountMove = self.env['account.move']
                                    moves = AccountMove.create(all_move_vals)
                                    moves.post()
        return res

    @api.onchange('state')
    def _onchange_update_cost_warehouse(self):
        for picking in self:
            if picking.group_id and picking.location_dest_id and picking.move_ids_without_package:
                for picking_line in picking.move_ids_without_package:
                    PurchaseOrder = self.env['purchase.order'].search([('name', '=', self.group_id.name)])
                    if len(PurchaseOrder) > 0:
                        orderline = PurchaseOrder.order_line
                        # line_order_id = orderline.filtered(lambda r: r.product_id.id == picking_line.product_id.id)
                        for line_order_id in orderline:
                            if line_order_id.product_id.id == picking_line.product_id.id:
                                warehouse = self.env['product.warehouse.cost'].search([('product_id','=',picking_line.product_id.id)])
                                if warehouse:
                                    cost_warehouse = warehouse.product_cost_line_ids.filtered(lambda r: r.warehouse_id.id == picking.location_dest_id.warehouse_id.id)
                                    if cost_warehouse:
                                        new_cost = ((cost_warehouse.cost * picking_line.product_id.qty_available) + (line_order_id.price_unit * picking_line.quantity_done)) / (picking_line.product_id.qty_available + picking_line.quantity_done)
                                        cost_warehouse.update({'cost' : new_cost})
                                        stock_val = self.env['stock.valuation.layer'].search([('product_id','=',picking_line.product_id.id), ('stock_move_id', '=', picking.move_lines.id), ('warehouse_id', '=', picking.location_dest_id.warehouse_id.id)])
                                        if stock_val:
                                            stock_val.update({'unit_cost': new_cost})

    