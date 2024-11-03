
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, date


class ShMpoMergePurchaseOrderWizard(models.TransientModel):
    _inherit = 'sh.mpo.merge.purchase.order.wizard'

    merge_option = fields.Selection(selection=[
        ('one_line', 'Merge into one product line'),
        ('multiple', 'Merge into multiple product line'),
    ], string='Merge Option', default='multiple')
    
    def action_merge_purchase_order(self):
        order_list = []
        picking_type_id = False
        context = dict(self.env.context) or {}
        purchase_order_ids = self.env['purchase.order'].browse(context.get('active_ids'))
        if self and self.partner_id and self.purchase_order_ids:
            if self.purchase_order_id:
                picking_type_id = self.purchase_order_id.picking_type_id.id
                order_list.append(self.purchase_order_id.id)
                order_line_vals = {"order_id": self.purchase_order_id.id}
                sequence = 10
                if self.purchase_order_id.order_line:
                    for existing_line in self.purchase_order_id.order_line:
                        existing_line.sudo().write({
                            'sequence':sequence
                            })
                        sequence+=1
                orders = self.env['purchase.order'].sudo().search([('id','!=',self.purchase_order_id.id),('id','in',self.purchase_order_ids.ids)],order='id asc')
                # if orders:
                #     if self.merge_option == 'one_line':
                #         product_id = self.env['purchase.order.line'].search([('order_id', 'in', orders.ids)]).mapped('product_id')
                for order in orders:
                    if order.order_line:
                        for line in order.order_line:
                            if self.merge_option != 'one_line':
                                merged_line = line.copy(default=order_line_vals)
                                merged_line.sudo().write({
                                    'sequence':sequence
                                    })
                                sequence+=1
                            else:
                                order_line_vals.update({'date_planned': line.date_planned})
                                lines = self.env['purchase.order.line'].search([('id', '!=', line.id),('order_id', '=', self.purchase_order_id.id),('date_planned', '=', line.date_planned),('destination_warehouse_id', '=', line.destination_warehouse_id.id)], limit=1)
                                if lines:
                                    price_unit = 0
                                    if line.price_unit > lines.price_unit:
                                        price_unit = line.price_unit
                                    else:
                                        price_unit = lines.price_unit
                                    lines.write({
                                        'analytic_tag_ids': [(4, analytic) for analytic in line.analytic_tag_ids.ids],
                                        'product_qty': line.product_qty + lines.product_qty,
                                        'price_unit': price_unit
                                    })
                                else:
                                    merged_line = line.copy(default=order_line_vals)
                                    merged_line.sudo().write({
                                        'sequence':sequence
                                    })
                                    sequence+=1


                    # finally cancel or remove order
                    if self.merge_type == "cancel":
                        order.sudo().button_cancel()
                        order_list.append(order.id)
                    elif self.merge_type == "remove":
                        order.sudo().button_cancel()
                        order.sudo().unlink()

            else:
                for i in self.purchase_order_ids:
                    if i.picking_type_id:
                        picking_type_id = i.picking_type_id.id
                is_rental_orders = False
                is_assets_orders = False
                if 'is_rental_orders' in purchase_order_ids[0]._fields:
                    is_rental_orders = purchase_order_ids.mapped('is_rental_orders')[0]
                if 'is_assets_orders' in purchase_order_ids[0]._fields:
                    is_assets_orders = purchase_order_ids.mapped('is_assets_orders')[0]
                if self.env['ir.config_parameter'].sudo().get_param('is_good_services_order') == 'True':
                # if self.env.company.is_good_services_order:
                    is_goods_orders = purchase_order_ids.mapped('is_goods_orders')[0]
                    is_services_orders = purchase_order_ids.mapped('is_services_orders')[0]
                    if is_goods_orders:
                        context.update({
                            'default_is_goods_orders': is_goods_orders,
                            "goods_order": True,
                        })
                    elif is_services_orders:
                        context.update({
                            'default_is_services_orders': is_services_orders,
                            'services_good': True,
                            })
                    elif is_assets_orders:
                        context.update({
                            'default_is_assets_orders': is_assets_orders,
                            'assets_orders': True,
                            })
                    elif is_rental_orders:
                        context.update({
                            'default_is_rental_orders': is_rental_orders,
                            'rentals_orders': True,
                            'is_rental_orders': True,
                        })
                else:
                    if is_rental_orders:
                        context.update({
                            'default_is_rental_orders': is_rental_orders,
                            'rentals_orders': True,
                            'is_rental_orders': True,
                        })
                    else:
                        context.update({'default_is_goods_orders': False})
                context.update({
                    "trigger_onchange": True,
                    "onchange_fields_to_trigger": [self.partner_id.id],
                })
                created_po = self.env["purchase.order"].with_context(context).create({"partner_id": self.partner_id.id,
                "date_planned": datetime.now(), 'is_delivery_receipt': False, 'picking_type_id': picking_type_id
               })
                created_po._onchange_partner_invoice_id()
                if created_po:
                    order_list.append(created_po.id)
                    order_line_vals = {"order_id": created_po.id}
                    sequence = 10
                    orders = self.env['purchase.order'].sudo().search([('id','in',self.purchase_order_ids.ids)],order='id asc')
                    for order in orders:
                        if order.order_line:
                            for line in order.order_line:
                                if self.merge_option != 'one_line':
                                    merged_line = line.copy(default=order_line_vals)
                                    merged_line.sudo().write({
                                        'sequence':sequence
                                    })
                                    sequence+=1
                                else:
                                    order_line_vals.update({'date_planned': line.date_planned})
                                    lines = self.env['purchase.order.line'].search([('id', '!=', line.id),('order_id', '=', created_po.id),('date_planned', '=', line.date_planned),('destination_warehouse_id', '=', line.destination_warehouse_id.id)], limit=1)
                                    if lines:
                                        price_unit = 0
                                        if line.price_unit > lines.price_unit:
                                            price_unit = line.price_unit
                                        else:
                                            price_unit = lines.price_unit
                                        lines.write({
                                            'analytic_tag_ids': [(4, analytic) for analytic in line.analytic_tag_ids.ids],
                                            'product_qty': line.product_qty + lines.product_qty,
                                            'price_unit': price_unit
                                        })
                                    else:
                                        merged_line = line.copy(default=order_line_vals)
                                        merged_line.sudo().write({
                                            'sequence':sequence
                                        })
                                        sequence+=1

                        # finally cancel or remove order
                        if self.merge_type == "cancel":
                            order.sudo().button_cancel()
                            order_list.append(order.id)
                        elif self.merge_type == "remove":
                            order.sudo().button_cancel()
                            order.sudo().unlink()
            if order_list:
                return {
                    "name": _("Requests for Quotation"),
                    "domain": [("id", "in", order_list)],
                    "view_type": "form",
                    "view_mode": "tree,form",
                    "res_model": "purchase.order",
                    "view_id": False,
                    "type": "ir.actions.act_window",
                }
