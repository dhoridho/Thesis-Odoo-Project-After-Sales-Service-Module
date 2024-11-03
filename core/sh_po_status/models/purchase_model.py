# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    sh_fully_ship = fields.Boolean(
        string="Fully Shipped", readonly=True, default=False)
    sh_partially_ship = fields.Boolean(
        string="Partially Shipped", readonly=True, default=False)
    sh_fully_paid = fields.Boolean(
        string="Fully Paid", readonly=True, default=False)
    sh_partially_paid = fields.Boolean(
        string="Partially Paid", readonly=True, default=False)
    sh_hidden_compute_field = fields.Boolean(
        string="Hidden Compute Shipment", readonly=True, compute="_compute_shipment")

    @api.depends("order_line.qty_received")
    def _compute_shipment(self):
        if self:
            for po_rec in self:
                po_rec.sh_hidden_compute_field = False
                if po_rec.order_line and not po_rec.sh_hidden_compute_field:
                    no_service_product_line = po_rec.order_line.filtered(
                        lambda line: (line.product_id) and (line.product_id.type != 'service'))
                    if no_service_product_line:
                        po_rec.write({"sh_fully_ship": False})
                        po_rec.write({"sh_partially_ship": False})
                        product_qty = qty_received = 0
                        for line in no_service_product_line:
                            qty_received += line.qty_received
                            product_qty += line.product_qty
                        if product_qty == qty_received:
                            po_rec.write({"sh_fully_ship": True})
                        elif product_qty > qty_received and qty_received != 0:
                            po_rec.write({"sh_partially_ship": True})

                if po_rec.invoice_ids and not po_rec.sh_hidden_compute_field:
                    sum_of_invoice_amount = 0.0
                    sum_of_due_amount = 0.0
                    po_rec.write({'sh_fully_paid': False})
                    po_rec.write({'sh_partially_paid': False})
                    for invoice_id in po_rec.invoice_ids.filtered(lambda inv: inv.state not in ['cancel', 'draft']):
                        sum_of_invoice_amount = sum_of_invoice_amount + invoice_id.amount_total
                        sum_of_due_amount = sum_of_due_amount + invoice_id.amount_residual
                        if invoice_id.amount_residual != 0 and invoice_id.amount_residual < invoice_id.amount_total:
                            po_rec.write({'sh_partially_paid': True})
                    if sum_of_due_amount == 0 and sum_of_invoice_amount >= po_rec.amount_total:
                        po_rec.write({'sh_fully_paid': True})
