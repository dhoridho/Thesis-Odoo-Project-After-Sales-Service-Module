# -*- coding: utf-8 -*-

from odoo import api, fields, models

class PosOrderLine(models.Model):
    _inherit = "pos.order.line"
    
    po_line_id = fields.Many2one(
        'purchase.order.line',
        string='Purchase Order Line'
    )
    custom_is_consignment = fields.Boolean(
        string='Is Consignment',
        copy= False
    )
    
    def _order_line_fields(self, line, session_id=None):
        res = super(PosOrderLine, self)._order_line_fields(line, session_id)
        browse_product = self.env['product.product'].browse(res[2].get('product_id', False))
        if browse_product and browse_product.custom_is_consignment and res[2]:
            # browse_product.write({
            #     'total_available_qty': browse_product.total_available_qty - res[2].get('qty'),
            #     'sale_qty': browse_product.sale_qty + res[2].get('qty'),
            #     'sale_price_total': browse_product.sale_price_total + res[2].get('price_unit'),
            # })
            res[2].update({
                # 'po_line_id': browse_product.purchase_order_line_id.id,
                'custom_is_consignment': True
            })
        return res

    @api.model
    def create(self, values):
        res = super(PosOrderLine, self).create(values)
        if res.custom_is_consignment:
            res.product_id.write({
                'pos_order_line_ids': [(4, res.id)],
            })
        return res

    def _prepare_refund_data(self, refund_order, PosOrderLineLot):
        self.ensure_one()
        self.custom_is_consignment = False
        return super(PosOrderLine, self)._prepare_refund_data(refund_order, PosOrderLineLot)