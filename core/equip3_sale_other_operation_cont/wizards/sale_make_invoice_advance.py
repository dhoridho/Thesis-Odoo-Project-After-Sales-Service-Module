# -*- coding: utf-8 -*-

from odoo import models


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def create_invoices(self):
        so = self.env['sale.order'].browse(self._context.get('active_id'))
        for line in so.order_line:
            if line.bo_id:
                bo_line = self.env['orderline.orderline'].browse(line.bo_id)
                invoiced_qty = bo_line.qty_invoiced
                sol = self.env['sale.order.line'].search([('id', '=', line.id)])
                for rec in sol:
                    invoiced_qty += rec.product_uom_qty
                    bo_line.write({'qty_invoiced': invoiced_qty})
        res = super(SaleAdvancePaymentInv, self).create_invoices()
        return res