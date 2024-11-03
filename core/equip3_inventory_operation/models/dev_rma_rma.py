
from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError


class dev_rma_rma(models.Model):
    _inherit = "dev.rma.rma"

    subject = fields.Char('Subject', required=False)
    picking_id = fields.Many2one('stock.picking', string='Delivery Order', required='1',
                                 domain="[('picking_type_id', '=', operation_type_id ), ('partner_id', '=', partner_id), ('state', '=', 'done'), ('is_complete_return', '=', False)]")
    partner_id = fields.Many2one(
        'res.partner', string='Partner', required=False)
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse",
                                   required=True, domain="[('company_id', '=', company_id)]")
    location_id = fields.Many2one(
        'stock.location', string="Location", required=True)
    sale_id = fields.Many2one(
        'sale.order', string='Sale Order', required=False)
    purchase_id = fields.Many2one(
        'purchase.order', string='Purchase Order', required=False)
    branch_id = fields.Many2one('res.branch', string="Branch",
                                default=lambda self: self.env.branches if len(
                                    self.env.branches) == 1 else False,
                                domain=lambda self: [('id', 'in', self.env.branches.ids)])
    filter_location_ids = fields.Many2many(
        'stock.location', string='Allowed Locations', compute='_get_filter_locations', store=False)
    operation_type_id = fields.Many2one('stock.picking.type', string="Operation Type", required=True,
                                        domain="['|', ('default_location_src_id', '=', location_id), ('default_location_dest_id', '=', location_id)]")
    picking_type_code = fields.Selection(related='operation_type_id.code')
    new_purchase_id = fields.Many2one(
        'purchase.order', string='New Purchase Order', copy=False)
    delivery_id = fields.Many2one(
        'stock.picking', string='Delivery Order', copy=False)
    receipt_id = fields.Many2one(
        'stock.picking', string='Receiving Notes', copy=False)
    state = fields.Selection([('draft', 'Draft'),
                              ('confirm', 'Confirmed'),
                              ('process', 'Processed'),
                              ('close', 'Done'),
                              ('reject', 'Reject')], string='State', default='draft', track_visibility='onchange')
    is_po = fields.Boolean(string='Is Purchase Order')
    return_possible_date = fields.Datetime(
        "Return Possible Date", compute="_compute_return_possible_date")
    is_return_order = fields.Boolean('Is Return Order', default=False)

    def action_close(self):
        self.ensure_one()
        res = super(dev_rma_rma, self).action_close()
        if self.is_return_order == True:
            wizard_pool = self.env['stock.return.picking']
            pro_vals = []
            for line in self.rma_lines:
                pro_vals.append((0, 0, {
                                'move_id': line.move_id.id,
                                'product_id': line.product_id.id,
                                'quantity': line.return_qty or 0.0,
                                'uom_id': line.move_id.product_uom.id,
                                'to_refund': True,
                                }))

            vals = {
                'picking_id': self.incoming_id.id,
                'parent_location_id': self.incoming_id.location_id.location_id.id,
                'original_location_id': self.incoming_id.location_id and self.incoming_id.location_id.id or False,
                'location_id': self.incoming_id.location_id and self.incoming_id.location_id.id or False,
                'product_return_moves': pro_vals,
            }
            wizard_id = wizard_pool.create(vals)
            refund = wizard_id.create_returns()
            self.delivery_id = refund.get('res_id')
            self.delivery_id.rma_id = self.id
        else:
            pass
        return res

    # def action_confirm(self):
    #     self.ensure_one()

    #     res = super(dev_rma_rma, self).action_confirm()
    #     for record in self:
    #         if not record.is_po and record.rma_lines.filtered(lambda a: a.action == 'repair'):
    #             lines = record.rma_lines.filtered(
    #                 lambda a: a.action == 'repair')
    #             context = dict(self.env.context) or {}
    #             repair_line_ids = [(0, 0, {
    #                 'product_id': line.product_id.id,
    #                 'quantity': line.return_qty,
    #                 'location_id': record.location_id.id,
    #             }) for line in lines]
    #             context.update({
    #                 'default_repair_line_ids': repair_line_ids,
    #                 'default_return_sale_order_id': self.id,
    #             })
    #             return {
    #                 'type': 'ir.actions.act_window',
    #                 'name': 'Return Requests of Sale Order',
    #                 'view_type': 'form',
    #                 'view_mode': 'form',
    #                 'res_model': 'sale.order.repair',
    #                 'target': 'new',
    #                 'context': context
    #             }
    #     return res

    @api.model
    def create(self, vals):
        res = super(dev_rma_rma, self).create(vals)
        if res.is_po:
            res.name = 'RPO' + res.name
        else:
            res.name = 'RSO' + res.name
        return res

    def action_view_receipt(self):
        self.ensure_one()

        receipt_id = [self.receipt_id.id]
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        if len(receipt_id) > 1:
            action['domain'] = [('id', 'in', receipt_id)]
        elif len(receipt_id) == 1:
            action['views'] = [
                (self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = receipt_id[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    @api.depends('warehouse_id')
    def _get_filter_locations(self):
        location_id = []
        for record in self:
            if record.warehouse_id:
                location_obj = record.env['stock.location']
                store_location_id = record.warehouse_id.view_location_id.id
                addtional_ids = location_obj.search(
                    [('location_id', 'child_of', store_location_id), ('usage', '=', 'internal')])
                for location in addtional_ids:
                    if location.location_id.id not in addtional_ids.ids:
                        location_id.append(location.id)
                record.filter_location_ids = [(6, 0, location_id)]
            else:
                record.filter_location_ids = [(6, 0, [])]

    @api.onchange('picking_id')
    def get_picking_id(self):
        if self.picking_id:
            self.sale_id = self.picking_id.group_id.sale_id.id
            self.purchase_id = self.picking_id.purchase_id.id
        else:
            self.sale_id = False

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        context = dict(self.env.context) or {}
        self.branch_id = self.warehouse_id.branch_id.id
        if context.get('default_is_po'):
            self.location_id = False
            self.operation_type_id = False
            self.picking_id = False
        if not context.get('default_is_po'):
            self.location_id = False
            self.operation_type_id = False
            self.picking_id = False

    @api.onchange('location_id')
    def get_location_operation_type(self):
        if self.is_po and self.location_id:
            default_dest_location_id = self.env['stock.picking.type'].search(
                [('default_location_dest_id', '=', self.location_id.id), ('code', '=', 'incoming')], limit=1)
            self.operation_type_id = default_dest_location_id.id
        elif self.location_id:
            default_location_src_id = self.env['stock.picking.type'].search(
                [('default_location_src_id', '=', self.location_id.id), ('code', '=', 'outgoing')], limit=1)
            self.operation_type_id = default_location_src_id.id

    @api.onchange('picking_id')
    def onchange_picking_id(self):
        if self.picking_id:
            self.partner_id = self.picking_id and self.picking_id.partner_id and self.picking_id.partner_id.id or False
            vals = []
            self.rma_lines = False
            for line in self.picking_id.move_lines:
                vals.append([0, 0, {
                            'move_id': line.id,
                            'product_id': line.product_id.id,
                            'product_description': line.product_description,
                            'delivered_qty': line.quantity_done or 0.0,
                            'action': 'refund',
                            'available_qty': line.initial_demand - line.return_qty
                            }])
            self.rma_lines = vals
        else:
            self.partner_id = False
            
    def action_dev_launch_procurment(self):
        res = super(dev_rma_rma, self).action_dev_launch_procurment()
        new_receipt_id = False
        vals = {
            'partner_id': self.partner_id.id,
            'picking_type_id': self.operation_type_id.id,
            'company_id': self.company_id.id,
            'user_id': self.create_uid.id,
            'date': datetime.now(),
            'origin': self.name,
            'location_id': self.location_id.id,
            'location_dest_id': self.warehouse_id._get_partner_locations()[0].id,
            
        }

        for line in self.rma_lines:
            if line.action == 'repair':
                if not new_receipt_id:
                    receipt_id = self.env['stock.picking'].create(vals)
                    new_receipt_id = receipt_id.id
                line_vals = {
                    'product_id': line.product_id.id,
                    'name': line.product_description,
                    'product_uom_qty': line.return_qty,
                    'product_uom': line.product_id and line.product_id.uom_id and line.product_id.uom_id.id or False,
                    'price_unit': line.product_id.lst_price or 0.0,
                    'picking_id': new_receipt_id,
                    'date': datetime.now(),
                    'state': 'draft',
                    'origin': self.name,
                    'warehouse_id': self.warehouse_id.id,
                    'location_id': self.location_id.id,
                    'location_dest_id': self.warehouse_id._get_partner_locations()[0].id,
                }
                self.env['stock.move'].create(line_vals)
            self.delivery_id = new_receipt_id
        return res

    def dev_process_rma(self):
        self.ensure_one()
        if self.picking_id.picking_type_code == 'outgoing':
            # create delivery order when replace with same product
            self.action_dev_launch_procurment()

            # turn off this function cause they want to create DO for product in function Done
            # self.action_dev_repair_launch_procurment() # create delivery order when repair

            self.action_create_sale_order()  # create sale order when replace with other product
            for r_line in self.rma_lines:
                if r_line.move_id and r_line.move_id.sale_line_id:
                    r_line.move_id.sale_line_id.is_process_rma = True
            if self.sale_id:
                sale_process = True
                for line in self.sale_id.order_line:
                    if not line.is_process_rma:
                        sale_process = False

                if sale_process and self.sale_id:
                    self.sale_id.is_process_rma = True

        elif self.picking_id.picking_type_code == 'incoming':
            # create receipt when replace with same product
            self.action_dev_launch_procurment_incoming()
            self.action_create_purchase_order()

        self.state = 'process'
        return True

    def action_dev_launch_procurment_incoming(self):
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        errors = []
        vals = {
            'partner_id': self.partner_id.id,
            'picking_type_id': self.operation_type_id.id,
            'company_id': self.company_id.id,
            'user_id': self.create_uid.id,
            'date': datetime.now(),
            'origin': self.name,
            'location_dest_id': self.location_id.id,
            'location_id': self.warehouse_id._get_partner_locations()[1].id,
        }
        new_receipt_id = False
        for line in self.rma_lines:
            if line.action == 'replace' and line.product_id.id == line.replace_product_id.id:
                if not new_receipt_id:
                    receipt_id = self.env['stock.picking'].create(vals)
                    new_receipt_id = receipt_id.id
                line_vals = {
                    'product_id': line.replace_product_id.id,
                    'name': line.replace_product_id.name,
                    'product_uom_qty': line.replace_qty,
                    'product_uom': line.replace_product_id and line.replace_product_id.uom_id and line.replace_product_id.uom_id.id or False,
                    'price_unit': line.replace_product_id.lst_price or 0.0,
                    'picking_id': new_receipt_id,
                    'date': datetime.now(),
                    'state': 'draft',
                    'origin': self.name,
                    'warehouse_id': self.warehouse_id.id,
                    'location_id': self.warehouse_id._get_partner_locations()[1].id,
                    'location_dest_id': self.location_id.id,
                }
                stock_move_id = self.env['stock.move'].create(line_vals)
            if line.action == 'repair':
                if not new_receipt_id:
                    receipt_id = self.env['stock.picking'].create(vals)
                    new_receipt_id = receipt_id.id
                line_vals = {
                    'product_id': line.product_id.id,
                    'name': line.product_description,
                    'product_uom_qty': line.return_qty,
                    'product_uom': line.product_id and line.product_id.uom_id and line.product_id.uom_id.id or False,
                    'price_unit': line.product_id.lst_price or 0.0,
                    'picking_id': new_receipt_id,
                    'date': datetime.now(),
                    'state': 'draft',
                    'origin': self.name,
                    'warehouse_id': self.warehouse_id.id,
                    'location_id': self.warehouse_id._get_partner_locations()[1].id,
                    'location_dest_id': self.location_id.id,
                }
                stock_move_id = self.env['stock.move'].create(line_vals)
        self.receipt_id = new_receipt_id
        return True

    def action_create_purchase_order(self):
        vals = {
            'partner_id': self.partner_id.id,
            'picking_type_id': self.operation_type_id.id,
            'company_id': self.company_id.id,
            'branch_id': self.branch_id.id,
        }
        new_purchase_id = False
        for line in self.rma_lines:
            if line.action == 'replace' and line.product_id.id != line.replace_product_id.id:
                if not new_purchase_id:
                    purchase_order = self.env['purchase.order'].create(vals)
                    new_purchase_id = purchase_order.id
                line_vals = {
                    'product_id': line.replace_product_id.id,
                    'name': line.replace_product_id.name,
                    'product_qty': line.replace_qty,
                    'product_uom': line.replace_product_id and line.replace_product_id.uom_id and line.replace_product_id.uom_id.id or False,
                    'price_unit': line.replace_product_id.lst_price or 0.0,
                    'order_id': new_purchase_id,
                    'destination_warehouse_id': self.warehouse_id.id,
                }
                purchase_line_id = self.env['purchase.order.line'].create(
                    line_vals)
                purchase_line_id.product_qty = line.replace_qty

        self.new_purchase_id = new_purchase_id
        return True

    def action_view_purchase_order(self):
        self.ensure_one()

        purchase_order_id = [self.new_purchase_id.id]
        action = self.env.ref('purchase.purchase_rfq').read()[0]
        if len(purchase_order_id) > 1:
            action['domain'] = [('id', 'in', purchase_order_id)]
        elif len(purchase_order_id) == 1:
            action['views'] = [
                (self.env.ref('purchase.purchase_order_form').id, 'form')]
            action['res_id'] = purchase_order_id[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def get_repair_purchase_line(self, product_id, move_id, purchase_line_ids=[]):
        for line in self.purchase_id.order_line:
            if line.product_id.id == product_id.id or move_id in line.move_ids.ids:
                if purchase_line_ids:
                    if line.id not in purchase_line_ids:
                        return line
                else:
                    return line

    def make_refund(self):
        self.ensure_one()

        if self.picking_type_code == 'incoming':
            wizard_id = self.env['dev.credit.note.wizard'].create(
                {'purchase_id': self.purchase_id.id, 'rma_id': self.id})
            line_pool = self.env['credit.note.product.lines']
            purchase_line_ids = []
            for line in self.rma_lines:
                purchase_line = False
                if line.action == 'refund':
                    purchase_line = self.get_repair_purchase_line(
                        line.product_id, line.move_id.id, purchase_line_ids)
                elif line.action == 'replace' and line.replace_product_id.id != line.product_id.id:
                    purchase_line = self.get_repair_purchase_line(
                        line.product_id, line.move_id.id, purchase_line_ids)
                if purchase_line and purchase_line.id not in purchase_line_ids:
                    purchase_line_ids.append(purchase_line.id)
                    line_pool.create({
                        'product_id': purchase_line.product_id.id,
                        'quantity': line.return_qty,
                        'price': purchase_line.price_unit,
                        'purchase_line_id': purchase_line and purchase_line.id or False,
                        'credit_note_id': wizard_id.id,
                    })
            return {
                "name": "Process Request",
                'view_mode': 'form',
                'res_id': wizard_id.id,
                'res_model': 'dev.credit.note.wizard',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'context': self._context,
                'target': 'new',
            }
        else:
            res = super(dev_rma_rma, self).make_refund()
            if res.get('context'):
                res['name'] = "Process Request"
            return res

    @api.onchange('picking_id')
    def _compute_return_possible_date(self):
        for rec in self:
            is_return_orders = bool(
                self.env['ir.config_parameter'].get_param('is_return_orders', False))
            rec.return_possible_date = self.picking_id.return_date_limit if is_return_orders and \
                self.picking_id.return_date_limit and \
                self.picking_id.return_date_limit < fields.Datetime.now() \
                else False

    def action_create_shipment(self):
        self.ensure_one()

        wizard_pool = self.env['stock.return.picking']
        pro_vals = []
        for line in self.rma_lines:
            pro_vals.append((0, 0, {
                            'move_id': line.move_id.id,
                            'product_id': line.product_id.id,
                            'quantity': line.return_qty or 0.0,
                            'uom_id': line.move_id.product_uom.id,
                            'to_refund': True,
                            'action': line.action,
                            'return_reason': line.return_reason.id
                            }))

        vals = {
            'picking_id': self.picking_id.id,
            'parent_location_id': self.picking_id.location_id.location_id.id,
            'original_location_id': self.picking_id.location_id and self.picking_id.location_id.id or False,
            'location_id': self.picking_id.location_id and self.picking_id.location_id.id or False,
            'product_return_moves': pro_vals,
        }
        wizard_id = wizard_pool.create(vals)
        refund = wizard_id.with_context(
            from_return_request_so_po=True).create_returns()
        self.incoming_id = refund.get('res_id')
        self.incoming_id.rma_id = self.id
        return True


class DevRmaLine(models.Model):
    _inherit = "dev.rma.line"

    rma_id = fields.Many2one('dev.rma.rma', string='Return Request')
    action = fields.Selection(selection_add=[
        ('return', "Return"),
    ])
    return_reason = fields.Many2one("return.reason", string="Reason")
    product_description = fields.Char(string='Product Description')
    available_qty = fields.Char(string='Available Qty', copy=False)

    @api.onchange('action')
    def _onchange_action(self):
        if self.action == "repair":
            self.return_reason = self.env.ref(
                "equip3_inventory_operation.damages_product_return_reason").id
        else:
            self.return_reason = False

    def create_repair_order(self):
        vals = {
            "product_id": self.product_id.id,
            "product_qty": self.return_qty,
            "product_uom": self.product_id.uom_id.id,
            "user_id": self.env.user.id,
            "location_id": self.rma_id.location_id.id,
            "company_id": self.rma_id.company_id.id
        }
        repair_order = self.env["repair.order"].create(vals)
        return repair_order

    @api.onchange('return_qty')
    def _onchange_return_qty(self):
        for line in self:
            matching_move = next((move for move in line.rma_id.picking_id.move_ids_without_package
                                  if move.product_id == line.product_id), None)

            if matching_move:
                remaining_qty = matching_move.quantity_done - matching_move.return_qty
                if line.return_qty > remaining_qty:
                    raise ValidationError(
                        _('Return quantity for the product "%s" cannot be greater than the remaining quantity (%s) to be returned.')
                        % (line.product_id.display_name, remaining_qty)
                    )
