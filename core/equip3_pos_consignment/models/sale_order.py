# -*- coding: utf-8 -*-
from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"
    _description = "Sales Order"

    def _prepare_confirmation_values(self):
        result = super(SaleOrder, self)._prepare_confirmation_values()
        query = '''
                    SELECT pol.id
                    FROM purchase_order_line AS pol 
                    LEFT JOIN purchase_order po ON po.id = pol.order_id
                    WHERE pol.sold_qty < pol.product_qty AND po.state = 'purchase' AND po.is_consignment = 'True'
                '''
        self.env.cr.execute(query)
        purchase_order_line_ids = self.env.cr.fetchall()
        purchase_order_line_ids = [line[0] for line in purchase_order_line_ids]
        purchase_order_line = self.env['purchase.order.line'].search([('id', 'in', purchase_order_line_ids)], order='create_date asc')
        ignore_po_line_ids = []
        for line in self.order_line:
            so_line_qty = line.product_uom_qty
            pos_line_unit_price = line.price_unit * so_line_qty
            for po_line in purchase_order_line.filtered(lambda x: x.product_id.id == line.product_id.id and x.id not in ignore_po_line_ids):
                if so_line_qty <= (po_line.product_qty - po_line.sold_qty):
                    po_line.sold_qty += so_line_qty
                    po_line.sold_price += pos_line_unit_price
                    break
                elif so_line_qty > (po_line.product_qty - po_line.sold_qty):
                    pos_line_unit_price -= line.price_unit * (po_line.product_qty - po_line.sold_qty)
                    po_line.sold_price += line.price_unit * (po_line.product_qty - po_line.sold_qty)
                    so_line_qty -= (po_line.product_qty - po_line.sold_qty)
                    po_line.sold_qty += (po_line.product_qty - po_line.sold_qty)
                    ignore_po_line_ids.append(po_line.id)
        return result
