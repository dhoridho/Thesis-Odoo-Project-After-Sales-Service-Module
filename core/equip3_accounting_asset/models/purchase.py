# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.tools.float_utils import float_compare, float_round
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError

from odoo.addons.purchase.models.purchase import PurchaseOrder as Purchase

# class PurchaseOrder(models.Model):
#     _inherit = 'purchase.order'

#     def button_approve(self, force=False):
#         result = super(PurchaseOrder, self).button_approve(force=force)
#         self._create_picking()
#         return result

    
#     def _create_picking(self):
#         # This function is copied from the equi3_accounting_operation module. 
#         # This aim to solve the bug in the Destination Location in Stock Picking.
        
#         StockPicking = self.env['stock.picking']
#         for order in self:
#             temp_data = []
#             final_data = []
#             for line in order.order_line:
#                 if {'date_planned': line.date_planned, 'warehouse_id': line.destination_warehouse_id.id} in temp_data:
#                     filter_lines = list(filter(lambda r:r.get('date_planned') == line.date_planned and r.get('warehouse_id') == line.destination_warehouse_id.id, final_data))
#                     if filter_lines:
#                         filter_lines[0]['lines'].append(line)
#                 else:
#                     temp_data.append({
#                         'date_planned': line.date_planned,
#                         'warehouse_id': line.destination_warehouse_id.id
#                     })
#                     final_data.append({
#                         'date_planned': line.date_planned,
#                         'warehouse_id': line.destination_warehouse_id.id,
#                         'lines': [line]
#                     })
#             for line_data in final_data:
#                 if any(product.type in ['product', 'consu', 'asset'] for product in order.order_line.product_id):
#                     order = order.with_company(order.company_id)
#                     pickings = order.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
#                     res = order._prepare_picking()
#                     warehouse_id = self.env['stock.warehouse'].browse([line_data.get('warehouse_id')])
#                     picking_type_id = self.env['stock.picking.type'].search([('warehouse_id', '=', warehouse_id.id), ('code', '=', 'incoming')], limit=1)
#                     if picking_type_id:
#                         res.update({
#                             'picking_type_id': picking_type_id.id,
#                             'location_dest_id': picking_type_id.default_location_dest_id.id,
#                             'date': line_data.get('date_planned'),
#                         })
#                     picking = StockPicking.with_user(SUPERUSER_ID).create(res)
#                     lines = self.env['purchase.order.line']
#                     for new_line in line_data.get('lines'):
#                         lines += new_line
#                     moves = lines._create_stock_moves(picking)
#                     moves = moves.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()
#                     seq = 0
#                     for move in sorted(moves, key=lambda move: move.date):
#                         seq += 5
#                         move.sequence = seq
#                     moves._action_assign()
#                     picking.message_post_with_view('mail.message_origin_link',
#                         values={'self': picking, 'origin': order},
#                         subtype_id=self.env.ref('mail.mt_note').id)
#         return True

# class PurchaseOrderLine(models.Model):
#     _inherit = 'purchase.order.line'

#     is_asset_type = fields.Boolean(compute='_compute_asset_type')

#     product_id = fields.Many2one('product.product', string='Product', domain=lambda self: self._get_product_domain(),
#                                  change_default=True)

#     @api.model
#     def _default_domain(self):
#         context = dict(self.env.context) or {}
#         if context.get('asset_goods'):
#             return [('type', '=', 'asset')]

#     def _compute_asset_type(self):
#         context = dict(self.env.context) or {}
#         if context.get('asset_goods'):
#             self.is_asset_type = True
#         else:
#             self.is_asset_type = False

#     def _get_product_domain(self):
#         domain = "[('purchase_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', parent.company_id)]"
#         context = dict(self.env.context) or {}
#         if context.get('asset_goods'):
#             domain = "[('purchase_ok', '=', True),('type', '=', 'asset'), '|', ('company_id', '=', False), ('company_id', '=', parent.company_id)]"
#         return domain

#     def _compute_qty_received_method(self):
#         super(PurchaseOrderLine, self)._compute_qty_received_method()
#         for line in self.filtered(lambda l: not l.display_type):
#             if line.product_id.type in ['consu', 'product', 'asset']:
#                 line.qty_received_method = 'stock_moves'

#     def _prepare_stock_moves(self, picking):
#         """ Prepare the stock moves data for one order line. This function returns a list of
#         dictionary ready to be used in stock.move's create()
#         """
#         self.ensure_one()
#         res = []
#         if self.product_id.type not in ['product', 'consu', 'asset']:
#             return res

#         price_unit = self._get_stock_move_price_unit()
#         qty = self._get_qty_procurement()

#         move_dests = self.move_dest_ids
#         if not move_dests:
#             move_dests = self.move_ids.move_dest_ids.filtered(
#                 lambda m: m.state != 'cancel' and not m.location_dest_id.usage == 'supplier')

#         if not move_dests:
#             qty_to_attach = 0
#             qty_to_push = self.product_qty - qty
#         else:
#             move_dests_initial_demand = self.product_id.uom_id._compute_quantity(
#                 sum(move_dests.filtered(
#                     lambda m: m.state != 'cancel' and not m.location_dest_id.usage == 'supplier').mapped(
#                     'product_qty')),
#                 self.product_uom, rounding_method='HALF-UP')
#             qty_to_attach = min(self.product_qty, move_dests_initial_demand) - qty
#             qty_to_push = self.product_qty - move_dests_initial_demand

#         if float_compare(qty_to_attach, 0.0, precision_rounding=self.product_uom.rounding) > 0:
#             product_uom_qty, product_uom = self.product_uom._adjust_uom_quantities(qty_to_attach,
#                                                                                    self.product_id.uom_id)
#             res.append(self._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom))
#         if float_compare(qty_to_push, 0.0, precision_rounding=self.product_uom.rounding) > 0:
#             product_uom_qty, product_uom = self.product_uom._adjust_uom_quantities(qty_to_push, self.product_id.uom_id)
#             extra_move_vals = self._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)
#             extra_move_vals['move_dest_ids'] = False  # don't attach
#             res.append(extra_move_vals)
#         return res

#     def _create_stock_moves(self, picking):
#         values = []
#         for line in self.filtered(lambda l: not l.display_type):
#             for val in line._prepare_stock_moves(picking):
#                 values.append(val)
#             line.move_dest_ids.created_purchase_line_id = False

#         return self.env['stock.move'].create(values)

#     def _create_or_update_picking(self):
#         for line in self:
#             if line.product_id and line.product_id.type in ('product', 'consu', 'asset'):
#                 # Prevent decreasing below received quantity
#                 if float_compare(line.product_qty, line.qty_received, line.product_uom.rounding) < 0:
#                     raise UserError(_('You cannot decrease the ordered quantity below the received quantity.\n'
#                                       'Create a return first.'))

#                 if float_compare(line.product_qty, line.qty_invoiced, line.product_uom.rounding) == -1:
#                     # If the quantity is now below the invoiced quantity, create an activity on the vendor bill
#                     # inviting the user to create a refund.
#                     line.invoice_lines[0].move_id.activity_schedule(
#                         'mail.mail_activity_data_warning',
#                         note=_('The quantities on your purchase order indicate less than billed. You should ask for a refund.'))

#                 # If the user increased quantity of existing line or created a new line
#                 pickings = line.order_id.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel') and x.location_dest_id.usage in ('internal', 'transit', 'customer'))
#                 picking = pickings and pickings[0] or False
#                 if not picking:
#                     res = line.order_id._prepare_picking()
#                     picking = self.env['stock.picking'].create(res)

#                 moves = line._create_stock_moves(picking)
#                 moves._action_confirm()._action_assign()

#     def _get_qty_procurement(self):
#         self.ensure_one()
#         qty = 0.0
#         outgoing_moves, incoming_moves = self._get_outgoing_incoming_moves()
#         for move in outgoing_moves:
#             qty -= move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom, rounding_method='HALF-UP')
#         for move in incoming_moves:
#             qty += move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom, rounding_method='HALF-UP')
#         return qty

#     def _get_stock_move_price_unit(self):
#         self.ensure_one()
#         line = self[0]
#         order = line.order_id
#         price_unit = line.price_unit
#         price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
#         if line.taxes_id:
#             qty = line.product_qty or 1
#             price_unit = line.taxes_id.with_context(round=False).compute_all(
#                 price_unit, currency=line.order_id.currency_id, quantity=qty, product=line.product_id,
#                 partner=line.order_id.partner_id
#             )['total_void']
#             price_unit = float_round(price_unit / qty, precision_digits=price_unit_prec)
#         if line.product_uom.id != line.product_id.uom_id.id:
#             price_unit *= line.product_uom.factor / line.product_id.uom_id.factor
#         if order.currency_id != order.company_id.currency_id:
#             price_unit = order.currency_id._convert(
#                 price_unit, order.company_id.currency_id, self.company_id, self.date_order or fields.Date.today(),
#                 round=False)
#         return price_unit

#     def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
#         self.ensure_one()
#         self._check_orderpoint_picking_type()
#         product = self.product_id.with_context(lang=self.order_id.dest_address_id.lang or self.env.user.lang)
#         description_picking = product._get_description(self.order_id.picking_type_id)
#         if self.product_description_variants:
#             description_picking += "\n" + self.product_description_variants
#         date_planned = self.date_planned or self.order_id.date_planned
#         return {
#             # truncate to 2000 to avoid triggering index limit error
#             # TODO: remove index in master?
#             'name': (self.name or '')[:2000],
#             'product_id': self.product_id.id,
#             'date': date_planned,
#             'date_deadline': date_planned + relativedelta(days=self.order_id.company_id.po_lead),
#             'location_id': self.order_id.partner_id.property_stock_supplier.id,
#             'location_dest_id': (self.orderpoint_id and not (self.move_ids | self.move_dest_ids)) and self.orderpoint_id.location_id.id or self.order_id._get_destination_location(),
#             'picking_id': picking.id,
#             'partner_id': self.order_id.dest_address_id.id,
#             'move_dest_ids': [(4, x) for x in self.move_dest_ids.ids],
#             'state': 'draft',
#             'purchase_line_id': self.id,
#             'company_id': self.order_id.company_id.id,
#             'price_unit': price_unit,
#             'picking_type_id': self.order_id.picking_type_id.id,
#             'group_id': self.order_id.group_id.id,
#             'origin': self.order_id.name,
#             'description_picking': description_picking,
#             'propagate_cancel': self.propagate_cancel,
#             'warehouse_id': self.order_id.picking_type_id.warehouse_id.id,
#             'product_uom_qty': product_uom_qty,
#             'product_uom': product_uom.id,
#         }

#     def _check_orderpoint_picking_type(self):
#         warehouse_loc = self.order_id.picking_type_id.warehouse_id.view_location_id
#         dest_loc = self.move_dest_ids.location_id or self.orderpoint_id.location_id
#         if warehouse_loc and dest_loc and dest_loc.get_warehouse() and not warehouse_loc.parent_path in dest_loc[0].parent_path:
#             raise UserError(_('For the product %s, the warehouse of the operation type (%s) is inconsistent with the location (%s) of the reordering rule (%s). Change the operation type or cancel the request for quotation.',
#                               self.product_id.display_name, self.order_id.picking_type_id.display_name, self.orderpoint_id.location_id.display_name, self.orderpoint_id.display_name))
