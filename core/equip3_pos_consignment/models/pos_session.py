# -*- coding: utf-8 -*-
from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _validate_session(self):
        result = super(PosSession, self)._validate_session()
        pos_order = self.env['pos.order'].search([('session_id', '=', self.id)])
        pos_order_lines = self.env['pos.order.line'].search([('order_id', 'in', pos_order.ids)])
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
        for pos_line in pos_order_lines:
            pos_line_qty = pos_line.qty
            pos_line_unit_price = pos_line.price_unit * pos_line_qty
            for po_line in purchase_order_line.filtered(lambda x: x.product_id.id == pos_line.product_id.id and x.id not in ignore_po_line_ids):
                if pos_line_qty <= (po_line.product_qty - po_line.sold_qty):
                    po_line.sold_qty += pos_line_qty
                    po_line.sold_price += pos_line_unit_price
                    break
                elif pos_line_qty > (po_line.product_qty - po_line.sold_qty):
                    pos_line_unit_price -= pos_line.price_unit * (po_line.product_qty - po_line.sold_qty)
                    po_line.sold_price += pos_line.price_unit * (po_line.product_qty - po_line.sold_qty)
                    pos_line_qty -= (po_line.product_qty - po_line.sold_qty)
                    po_line.sold_qty += (po_line.product_qty - po_line.sold_qty)
                    ignore_po_line_ids.append(po_line.id)
        return result
