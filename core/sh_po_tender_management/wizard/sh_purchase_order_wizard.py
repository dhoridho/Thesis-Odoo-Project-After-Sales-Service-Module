# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, _


class ShPurchaseOrderWizard(models.TransientModel):
    _name = 'purchase.order.wizard'
    _description = 'Purchase Order Wizard'

    sh_group_by_partner = fields.Boolean("Group By")
    sh_cancel_old_rfqs = fields.Selection([('none', 'None'), ('cancel_all_old', "Cancel Old RFQ'S of Tender"), ('cancel_old_partner', "Cancel Old RFQ'S of Selected Tender of Partners")],
                                          default='none',
                                          string="Cancel Old RFQ'S"
                                          )
    sh_create_po = fields.Selection([
        ('rfq', 'RFQ'),
        ('po', 'Purchase Order')
    ], default='rfq', string="Create RFQ/Purchase Order")

    def action_create_po(self):
        context = dict(self._context or {})
        purchase_order_line = self.env['purchase.order.line'].sudo().search(
            [('id', 'in', context.get('active_ids'))])
        if self.sh_cancel_old_rfqs == 'cancel_all_old':
            for line in purchase_order_line:
                purchase_orders = self.env['purchase.order'].sudo().search(
                    [('agreement_id', '=', line.agreement_id.id), ('state', 'in', ['draft'])])
                if purchase_orders:
                    for order in purchase_orders:
                        order.button_cancel()
        elif self.sh_cancel_old_rfqs == 'cancel_old_partner':
            partner_list = []
            agreement_list = []
            for order_line in purchase_order_line:
                if order_line.partner_id and order_line.partner_id not in partner_list:
                    partner_list.append(order_line.partner_id.id)
                if order_line.agreement_id and order_line.agreement_id not in agreement_list:
                    agreement_list.append(order_line.agreement_id.id)
            purchase_orders = self.env['purchase.order'].sudo().search(
                [('state', 'in', ['draft'])])
            if purchase_orders:
                for order in purchase_orders:
                    if order.partner_id.id in partner_list and order.agreement_id.id in agreement_list:
                        order.button_cancel()
        if purchase_order_line:
            if not self.sh_group_by_partner:
                order_ids = []
                for order_line in purchase_order_line:
                    purchase_order_id = self.env['purchase.order'].sudo().create({
                        'partner_id': order_line.partner_id.id,
                        'date_order': fields.Datetime.now(),
                        'agreement_id': order_line.agreement_id.id,
                        'user_id': self.env.user.id,
                        'date_planned': order_line.date_planned,
                    })
                    order_ids.append(purchase_order_id.id)
                    line_vals = {
                        'order_id': purchase_order_id.id,
                        'product_id': order_line.product_id.id,
                        'name': order_line.product_id.name,
                        'date_planned': order_line.date_planned,
                        'status': 'draft',
                        'product_uom': order_line.product_id.uom_id.id,
                        'product_qty': order_line.product_qty,
                        'price_unit': order_line.price_unit,
                        'taxes_id': [(6, 0, order_line.taxes_id.ids)]
                    }
                    purchase_order_line = self.env['purchase.order.line'].sudo().create(
                        line_vals)
                    if self.sh_create_po == 'po':
                        purchase_order_id.selected_order = True
                        purchase_order_id.button_confirm()
                    else:
                        purchase_order_id.selected_order = False
                return {
                    'name': _("Purchase Orders/RFQ's"),
                    'type': 'ir.actions.act_window',
                    'res_model': 'purchase.order',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'domain': [('id', 'in', order_ids), ('selected_order', '=', True)],
                    'target': 'current'
                }
            else:
                partner_list = []
                agreement_id = None
                order_ids = []
                for order_line in purchase_order_line:
                    if order_line.partner_id and order_line.partner_id not in partner_list:
                        partner_list.append(order_line.partner_id)
                    agreement_id = order_line.agreement_id.id
                for partner in partner_list:
                    order_vals = {}
                    order_vals = {
                        'partner_id': partner.id,
                        'user_id': self.env.user.id,
                        'date_order': fields.Datetime.now(),
                        'agreement_id': agreement_id,
                    }
                    order_id = self.env['purchase.order'].create(order_vals)
                    order_ids.append(order_id.id)
                    line_ids = []
                    for order_line in purchase_order_line:
                        if order_line.partner_id.id == partner.id:
                            order_line_vals = {
                                'order_id': order_id.id,
                                'product_id': order_line.product_id.id,
                                'name': order_line.product_id.name,
                                'date_planned': order_line.date_planned,
                                'status': 'draft',
                                'product_uom': order_line.product_id.uom_id.id,
                                'product_qty': order_line.product_qty,
                                'price_unit': order_line.price_unit,
                                'taxes_id': [(6, 0, order_line.taxes_id.ids)]
                            }
                            line_ids.append((0, 0, order_line_vals))
                    order_id.order_line = line_ids
                    if self.sh_create_po == 'po':
                        order_id.selected_order = True
                        order_id.button_confirm()
                    else:
                        order_id.selected_order = False
                return {
                    'name': _("Purchase Orders/RFQ's"),
                    'type': 'ir.actions.act_window',
                    'res_model': 'purchase.order',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'domain': [('id', 'in', order_ids), ('selected_order', '=', True)],
                    'target': 'current'
                }
