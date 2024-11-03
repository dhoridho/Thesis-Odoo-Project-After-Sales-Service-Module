from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.tools import float_compare
from itertools import groupby


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_view_picking(self):
        self.ensure_one()

        result = self.env["ir.actions.actions"]._for_xml_id(
            'equip3_inventory_operation.stock_picking_receiving_note')
        pick_ids = self.mapped('picking_ids')
        # choose the view_mode accordingly
        if not pick_ids or len(pick_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % (pick_ids.ids)
        elif len(pick_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + \
                    [(state, view)
                     for state, view in result['views'] if view != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = pick_ids.id
        return result

    def button_approve(self, force=False):
        self.ensure_one()

        context = dict(self.env.context) or {}
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        product_service_operation_receiving = IrConfigParam.get_param(
            'is_product_service_operation_receiving', False)
        is_rn_approval_matrix_on = eval(IrConfigParam.get_param('is_receiving_notes_approval_matrix', 'False'))

        self = self.with_context(
            is_product_service_operation_receiving=product_service_operation_receiving,
            do_not_confirm_moves=is_rn_approval_matrix_on)
        return super(PurchaseOrder, self).button_approve(force=force)

    def _create_picking_service(self):
        StockPicking = self.env['stock.picking']
        for order in self.filtered(lambda po: po.state in ('purchase', 'done')):
            for order in self:
                sorted_line = sorted(order.order_line, key=lambda x: x.date_planned and x.destination_warehouse_id.id)
                final_data = [list(result) for key, result in groupby(
                    sorted_line, key=lambda x: x.date_planned and x.destination_warehouse_id.id)]
                for line_data in final_data:
                    if any(product.type in ['service'] for product in order.order_line.product_id):
                        order = order.with_company(order.company_id)
                        pickings = order.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
                        res = order._prepare_picking()
                        warehouse_id = line_data[0].mapped('destination_warehouse_id')
                        date_planned = line_data[0].mapped('date_planned')[0]
                        picking_type_id = self.env['stock.picking.type'].search([('warehouse_id', '=', warehouse_id.id), ('code', '=', 'incoming')], limit=1)
                        if picking_type_id:
                            res.update({
                                'picking_type_id': picking_type_id.id,
                                'location_dest_id': picking_type_id.default_location_dest_id.id,
                                'date': date_planned,
                            })
                        if warehouse_id.default_receipt_location_id:
                            res.update({
                                'location_dest_id':warehouse_id.default_receipt_location_id.id,
                            })
                        picking = StockPicking.with_user(SUPERUSER_ID).create(res)
                        lines = self.env['purchase.order.line']
                        for new_line in line_data:
                            lines += new_line
                        moves = lines._create_stock_moves_service(picking)
                        moves = moves._action_confirm()
                        seq = 0
                        for move in sorted(moves, key=lambda move: move.date):
                            seq += 5
                            move.sequence = seq
                        moves._action_assign()
                        picking.message_post_with_view('mail.message_origin_link',
                            values={'self': picking, 'origin': order},
                            subtype_id=self.env.ref('mail.mt_note').id)

    def _create_picking(self):
        res = super(PurchaseOrder, self)._create_picking()
        context = dict(self.env.context) or {}
        if context.get('is_product_service_operation_receiving'):
            self._create_picking_service()
        return res

    def _prepare_picking(self):
        res = super(PurchaseOrder, self)._prepare_picking()
        rn_approval_matrix_config = self.env['ir.config_parameter'].sudo().get_param('is_receiving_notes_approval_matrix', False)
        res.update({'is_rn_request_approval_matrix': rn_approval_matrix_config})
        return res


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _get_account_computed_account(self, move_id):
        self.ensure_one()
        if not self.product_id:
            return

        fiscal_position = move_id.fiscal_position_id
        accounts = self.product_id.product_tmpl_id.get_product_accounts(
            fiscal_pos=fiscal_position)
        if move_id.is_sale_document(include_receipts=True):
            # Out invoice.
            return accounts['income']
        elif move_id.is_purchase_document(include_receipts=True):
            # In invoice.
            # return accounts['expense']
            return accounts['stock_input']

    def _dev_invoice_line_val(self, invoice_id, quantity, price=0):
        """
        Prepare the dict of values to create the new invoice line for a sales order line.

        :param qty: float quantity to invoice
        """
        # self.ensure_one()
        if price == 0:
            price = self.price_unit
        val = {
            'display_type': self.display_type,
            'sequence': self.sequence,
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'quantity': quantity,
            'price_unit': price,
            'tax_ids': [(6, 0, self.taxes_id.ids)],
            'analytic_account_id': self.account_analytic_id.id,
            'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
            'purchase_line_id': self.id,
            'move_id': invoice_id.id,
            'account_id': self._get_account_computed_account(invoice_id).id,
        }
        return val

    def _create_stock_moves_service(self, picking):
        values = []
        for line in self.filtered(lambda l: not l.display_type):
            for val in line._prepare_stock_moves_services(picking):
                values.append(val)
            line.move_dest_ids.created_purchase_line_id = False

        return self.env['stock.move'].create(values)

    def _prepare_stock_moves_services(self, picking):
        """ Prepare the stock moves data for one order line. This function returns a list of
        dictionary ready to be used in stock.move's create()
        """
        context = dict(self.env.context) or {}
        if context.get('is_product_service_operation_receiving'):
            self.ensure_one()
            res = []
            if self.product_id.type in ['product', 'consu'] or not self.product_id.is_product_service_operation_receiving:
                return res

            qty = 0.0
            price_unit = self._get_stock_move_price_unit()
            outgoing_moves, incoming_moves = self._get_outgoing_incoming_moves()
            for move in outgoing_moves:
                qty -= move.product_uom._compute_quantity(
                    move.product_uom_qty, self.product_uom, rounding_method='HALF-UP')
            for move in incoming_moves:
                qty += move.product_uom._compute_quantity(
                    move.product_uom_qty, self.product_uom, rounding_method='HALF-UP')

            move_dests = self.move_dest_ids
            if not move_dests:
                move_dests = self.move_ids.move_dest_ids.filtered(
                    lambda m: m.state != 'cancel' and not m.location_dest_id.usage == 'supplier')

            if not move_dests:
                qty_to_attach = 0
                qty_to_push = self.product_qty - qty
            else:
                move_dests_initial_demand = self.product_id.uom_id._compute_quantity(
                    sum(move_dests.filtered(lambda m: m.state !=
                        'cancel' and not m.location_dest_id.usage == 'supplier').mapped('product_qty')),
                    self.product_uom, rounding_method='HALF-UP')
                qty_to_attach = move_dests_initial_demand - qty
                qty_to_push = self.product_qty - move_dests_initial_demand

            if float_compare(qty_to_attach, 0.0, precision_rounding=self.product_uom.rounding) > 0:
                product_uom_qty, product_uom = self.product_uom._adjust_uom_quantities(
                    qty_to_attach, self.product_id.uom_id)
                res.append(self._prepare_stock_move_vals(
                    picking, price_unit, product_uom_qty, product_uom))
            if float_compare(qty_to_push, 0.0, precision_rounding=self.product_uom.rounding) > 0:
                product_uom_qty, product_uom = self.product_uom._adjust_uom_quantities(
                    qty_to_push, self.product_id.uom_id)
                extra_move_vals = self._prepare_stock_move_vals(
                    picking, price_unit, product_uom_qty, product_uom)
                extra_move_vals['move_dest_ids'] = False  # don't attach
                res.append(extra_move_vals)
            return res
