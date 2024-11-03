# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright 2019 EquickERP
#
##############################################################################

from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.tools import float_compare


class purchase_order(models.Model):
    _inherit = 'purchase.order'

    def _create_picking(self):
        StockPicking = self.env['stock.picking']
        for order in self:
            if order.order_line.filtered(lambda l: l.product_id.type in ['product', 'consu']):
                order = order.with_company(order.company_id)
                for line in order.order_line.filtered(lambda l: l.product_id.type in ['product', 'consu']):
                    pickings = order.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel') and x.picking_type_id.id == line.picking_type_id.id)
                    if not pickings:
                        res = order.with_context(line_picking_type_id=line.picking_type_id.id)._prepare_picking()
                        picking = StockPicking.with_user(SUPERUSER_ID).create(res)
                    else:
                        picking = pickings[0]
                    moves = line._create_stock_moves(picking)
                    moves = moves.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()
                    seq = 0
                    for move in sorted(moves, key=lambda move: move.date):
                        seq += 5
                        move.sequence = seq
                    moves._action_assign()
                    picking.message_post_with_view('mail.message_origin_link',
                        values={'self': picking, 'origin': order},
                        subtype_id=self.env.ref('mail.mt_note').id)
                return True
            else:
                return super()._create_picking()

    def _prepare_picking(self):
        res = super(purchase_order, self)._prepare_picking()
        ctx = self.env.context
        if ctx.get('line_picking_type_id'):
            type_id = self.env['stock.picking.type'].browse(ctx['line_picking_type_id'])
            res.update({'picking_type_id': ctx['line_picking_type_id'],
                        'company_id': type_id.company_id.id,
                        'location_dest_id': type_id.default_location_dest_id.id,
                        })
        return res


class purchase_order_line(models.Model):
    _inherit = 'purchase.order.line'

    picking_type_id = fields.Many2one('stock.picking.type', string='Deliver To')

    @api.onchange('product_id')
    def onchange_custom_product_id(self):
        self.picking_type_id = self.order_id.picking_type_id

    def _prepare_stock_moves(self, picking):
        template = super(purchase_order_line, self)._prepare_stock_moves(picking)
        if template:
            for each in template:
                each.update({'picking_type_id': self.picking_type_id.id,
                            'company_id': picking.company_id.id,
                            'route_ids': self.picking_type_id.warehouse_id and [(6, 0, [x.id for x in self.picking_type_id.warehouse_id.route_ids])] or [],
                            'location_dest_id': self.picking_type_id.default_location_dest_id.id
                })
        return template

    def _create_or_update_picking(self):
        for line in self:
            if line.product_id and line.product_id.type in ('product', 'consu'):
                # Prevent decreasing below received quantity
                if float_compare(line.product_qty, line.qty_received, line.product_uom.rounding) < 0:
                    raise UserError(_('You cannot decrease the ordered quantity below the received quantity.\n'
                                      'Create a return first.'))

                if float_compare(line.product_qty, line.qty_invoiced, line.product_uom.rounding) == -1:
                    # If the quantity is now below the invoiced quantity, create an activity on the vendor bill
                    # inviting the user to create a refund.
                    line.invoice_lines[0].move_id.activity_schedule(
                        'mail.mail_activity_data_warning',
                        note=_('The quantities on your purchase order indicate less than billed. You should ask for a refund.'))

                # If the user increased quantity of existing line or created a new line
                pickings = line.order_id.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel') and x.location_dest_id.usage in ('internal', 'transit', 'customer') and x.picking_type_id.id == line.picking_type_id.id)
                picking = pickings and pickings[0] or False
                if not picking:
                    res = line.order_id.with_context(line_picking_type_id=line.picking_type_id.id)._prepare_picking()
                    picking = self.env['stock.picking'].create(res)
                moves = line._create_stock_moves(picking)
                moves._action_confirm()._action_assign()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: