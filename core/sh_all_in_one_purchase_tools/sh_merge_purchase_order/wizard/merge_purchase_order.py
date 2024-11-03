# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError

class ResConfigSetting(models.TransientModel):
    _inherit = 'res.config.settings'

    group_enable_merge_purchase_order = fields.Boolean(
        "Enable Merge Purchase Order", implied_group='sh_all_in_one_purchase_tools.group_enable_merge_purchase_order')

class ShMpoMergePurchaseOrderWizard(models.TransientModel):
    _name = "sh.mpo.merge.purchase.order.wizard"
    _description = "Merge Purchase Order Wizard"

    partner_id = fields.Many2one("res.partner", string="Vendor", required=True)
    purchase_order_id = fields.Many2one(
        "purchase.order", string="Purchase Order")
    purchase_order_ids = fields.Many2many(
        "purchase.order", string="Purchase Orders")

    merge_type = fields.Selection([
        ("nothing", "Do Nothing"),
        ("cancel", "Cancel Other Purchase Orders"),
        ("remove", "Remove Other Purchase Orders"),
    ], default="nothing", string="Merge Type")

    @api.onchange("partner_id")
    def onchange_partner_id(self):
        if self:
            self.purchase_order_id = False

    def action_merge_purchase_order(self):
        order_list = []
        if self and self.partner_id and self.purchase_order_ids:
            if self.purchase_order_id:
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
                for order in orders:
                    if order.order_line:
                        for line in order.order_line:
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
                created_po = self.env["purchase.order"].with_context({
                    "trigger_onchange": True,
                    "onchange_fields_to_trigger": [self.partner_id.id]
                }).create({"partner_id": self.partner_id.id,
                           "date_planned": datetime.now(),
                           })
                if created_po:
                    order_list.append(created_po.id)
                    order_line_vals = {"order_id": created_po.id}
                    sequence = 10
                    orders = self.env['purchase.order'].sudo().search([('id','in',self.purchase_order_ids.ids)],order='id asc')
                    for order in orders:
                        if order.order_line:
                            for line in order.order_line:
                                merged_line = line.copy(default=order_line_vals)
                                merged_line.sudo().write({
                                    'sequence':sequence
                                    })
                                sequence +=1

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

    @api.model
    def default_get(self, fields):
        rec = super(ShMpoMergePurchaseOrderWizard, self).default_get(fields)
        active_ids = self._context.get("active_ids")

        if not self.env.user.has_group('sh_all_in_one_purchase_tools.group_enable_merge_purchase_order'):
            raise ValidationError(
                _("Enable Configuration for Merge Purchase Order"))
            
        # Check for selected invoices ids
        if not active_ids:
            raise UserError(
                _("Programming error: wizard action executed without active_ids in context."))

        # Check if only one purchase order selected.
        if len(self._context.get("active_ids", [])) < 2:
            raise UserError(
                _("Please Select atleast two Requests for Quotation to perform merge operation."))

        purchase_orders = self.env["purchase.order"].browse(active_ids)

        # Check all purchase order are draft state
        if any(order.state not in ["draft", "sent"] for order in purchase_orders):
            raise UserError(
                _("You can only merge purchase orders which are in RFQ and RFQ Sent state"))

        # return frist purchase order partner id and purchase order ids,
        rec.update({
            "partner_id": purchase_orders[0].partner_id.id if purchase_orders[0].partner_id else False,
            "purchase_order_ids": [(6, 0, purchase_orders.ids)],
        })
        return rec
