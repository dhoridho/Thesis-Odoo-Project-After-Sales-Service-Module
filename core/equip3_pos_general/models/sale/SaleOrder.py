# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta
from lxml import etree

class sale_order(models.Model):
    _inherit = "sale.order"

    book_order = fields.Boolean('Book Order')
    ean13 = fields.Char('Ean13', readonly=1)
    pos_config_id = fields.Many2one(
        'pos.config',
        string='Assign to POS',
    )
    pos_location_id = fields.Many2one(
        'stock.location',
        domain=[('usage', '=', 'internal')],
        help='All Point Of sale have the same with this Stock will have found this Order',
        string='Delivery Stock Location')
    delivery_date = fields.Datetime('Delivery Date of Bill')
    delivered_date = fields.Datetime('Delivered Date of Bill')
    delivery_address = fields.Char('Delivery Address of Bill')
    delivery_phone = fields.Char('Delivery Phone of Bill', help='Phone of customer for delivery')
    payment_partial_amount = fields.Float(
        'Partial Payment Amount',
    )
    payment_partial_method_id = fields.Many2one(
        'pos.payment.method',
        string='Payment Method'
    )
    insert = fields.Boolean('Insert', default=0)
    state = fields.Selection(selection_add=[
        ('booked', 'Converted to POS Order')
    ], ondelete={
        'booked': 'set default',
    })
    pos_branch_id = fields.Many2one(
        'res.branch',
        string='Branch',
        readonly=1
    )
    pos_order_id = fields.Many2one(
        'pos.order',
        'POS Order',
        readonly=1,
        copy=False
    )
    is_self_pickup = fields.Boolean('Self Pickup')

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=False, submenu=False):
        res = super(sale_order, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        user_pos_not_create_edit =  self.env.user.has_group('equip3_pos_masterdata.group_pos_cashier') or self.env.user.has_group('equip3_pos_masterdata.group_pos_waiter') or self.env.user.has_group('equip3_pos_masterdata.group_pos_cooker')
        user_pos_have_create_edit =  self.env.user.has_group('equip3_pos_masterdata.group_pos_staff') or self.env.user.has_group('equip3_pos_masterdata.group_pos_supervisor') or self.env.user.has_group('equip3_pos_masterdata.group_pos_manager')
        if user_pos_not_create_edit and not user_pos_have_create_edit:
            root = etree.fromstring(res['arch'])
            root.set('edit', 'false')
            res['arch'] = etree.tostring(root)

        if self.env.user.has_group('equip3_pos_masterdata.group_pos_user') and not self.env.user.has_group('equip3_pos_masterdata.group_pos_manager'):
            root = etree.fromstring(res['arch'])
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
            
        return res

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        context = self._context.copy()
        if context.get('pos_config_id', None):
            config = self.env['pos.config'].browse(context.get('pos_config_id'))
            domain = ['|', ('pos_config_id', '=', config.id), ('pos_config_id', '=', None)]
            if config.booking_orders_load_orders_another_pos:
                domain = []
            today = datetime.today()
            if config.load_booked_orders_type == 'load_all':
                domain = domain
            if config.load_booked_orders_type == 'last_3_days':
                loadFromDate = today + timedelta(days=-3)
                domain.append(('create_date', '>=', loadFromDate))
            if config.load_booked_orders_type == 'last_7_days':
                loadFromDate = today + timedelta(days=-7)
                domain.append(('create_date', '>=', loadFromDate))
            if config.load_booked_orders_type == 'last_1_month':
                loadFromDate = today + timedelta(days=-30)
                domain.append(('create_date', '>=', loadFromDate))
            if config.load_booked_orders_type == 'last_1_year':
                loadFromDate = today + timedelta(days=-365)
                domain.append(('create_date', '>=', loadFromDate))
        return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.onchange('pos_config_id')
    def onchange_pos_config_id(self):
        if self.pos_config_id:
            self.pos_location_id = self.pos_config_id.stock_location_id


    def action_confirm(self):
        res = super(sale_order, self).action_confirm()
        for data in self:
            if data.is_self_pickup:
                for picking in data.picking_ids:
                    if picking.state == 'draft':
                        picking.action_request_for_approval_do()
        return res

    def action_force_validate_picking(self):
        picking_name = ''
        for sale in self:
            for picking in sale.picking_ids:
                picking.action_confirm()
                picking.action_assign()
                #Set Done Qty
                for move in picking.move_lines.filtered(lambda m: m.state not in ['done', 'cancel']):
                    for move_line in move.move_line_ids:
                        move_line.qty_done = move_line.product_uom_qty
                picking.force_validate()
                picking_name = picking.name


        return picking_name

    def action_validate_picking(self):
        picking_name = ''
        for sale in self:
            for picking in sale.picking_ids:
                if picking.state in ['assigned', 'waiting', 'confirmed']:
                    for move_line in picking.move_line_ids:
                        move_line.write({'qty_done': move_line.product_uom_qty})
                    for move_line in picking.move_lines:
                        move_line.write({'quantity_done': move_line.product_uom_qty})
                    picking.button_validate()
                    picking_name = picking.name
        return picking_name

    @api.model
    def pos_create_sale_order(self, vals, sale_order_auto_confirm, sale_order_auto_invoice, sale_order_auto_delivery):
        sale = self.create(vals)
        sale.order_line._compute_tax_id()
        if sale_order_auto_confirm:
            for order_line in sale.order_line:
                query_statement = """UPDATE sale_order_line set multiple_do_date_new = %s WHERE id = %s """
                self.sudo().env.cr.execute(query_statement, [sale.commitment_date, order_line.id])

            sale.action_confirm()
            sale.action_done()
        if sale_order_auto_delivery and sale.picking_ids:
            for picking in sale.picking_ids:
                for move_line in picking.move_line_ids:
                    move_line.write({'qty_done': move_line.product_uom_qty})
                for move_line in picking.move_lines:
                    move_line.write({'quantity_done': move_line.product_uom_qty})
                picking.button_validate()
        if sale_order_auto_confirm and sale_order_auto_invoice:
            ctx = {'active_ids': [sale.id]}
            payment = self.env['sale.advance.payment.inv'].with_context(ctx).create({
                'advance_payment_method': 'fixed',
                'fixed_amount': sale.amount_total,
            })
            payment.create_invoices()
        return {'name': sale.name, 'id': sale.id}

    @api.model
    def booking_order(self, vals):
        so = self.create(vals)
        return {'name': so.name, 'id': so.id}

    @api.model
    def create(self, vals):
        if not vals.get('pos_branch_id'):
            vals.update({'pos_branch_id': self.env['res.branch'].sudo().get_default_branch()})
        sale = super(sale_order, self).create(vals)
        if not sale.delivery_address:
            if sale.partner_shipping_id:
                sale.delivery_address = sale.partner_shipping_id.contact_address
            else:
                sale.delivery_address = sale.partner_id.contact_address
        return sale

    def write(self, vals):
        res = super(sale_order, self).write(vals)
        for sale in self:
            if not sale.delivery_address:
                if sale.partner_shipping_id:
                    sale.delivery_address = sale.partner_shipping_id.contact_address
                else:
                    sale.delivery_address = sale.partner_id.contact_address
        return res

    def action_confirm_self_picking(self):
        context = self._context.copy()
        context.pop('default_name', None)
        self.with_context(context)._action_confirm()
        self.action_done()
        return True


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    insert = fields.Boolean('Insert', default=0)
    parent_id = fields.Many2one('sale.order.line', 'Parent')
    lot_id = fields.Many2one('stock.production.lot', 'Lot')
    pos_note = fields.Text('Booking Note')
    pos_branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])

    @api.model
    def create(self, vals):
        if not vals.get('pos_branch_id'):
            vals.update({'pos_branch_id': self.env['res.branch'].sudo().get_default_branch()})
        line = super(SaleOrderLine, self).create(vals)
        if line.insert:
            line.order_id.write({'insert': True})
        return line

    def _prepare_procurement_values(self, group_id=False):
        values = super(SaleOrderLine, self)._prepare_procurement_values(group_id)
        if self.order_id.pos_location_id:
            values.update({'location_id': self.order_id.pos_location_id.id})
        return values
