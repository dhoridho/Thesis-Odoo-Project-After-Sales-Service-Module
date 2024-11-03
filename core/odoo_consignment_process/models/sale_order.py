# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    is_consignment = fields.Boolean(
        string='Is Consignment',
    )
    consignment_purchase_order_count = fields.Integer(
        string="Purchase Count",
        compute="_consignment_purchase_order_count",
    )

    @api.depends()
    def _consignment_purchase_order_count(self):
        for rec in self:
            rec.consignment_purchase_order_count = self.env['sale.order.line'].search_count([
                ('order_id', '=', rec.id),
                ('purchase_order_line_id', '!=', False)
            ])

#    @api.multi #odoo13
    def show_consignment_purchase_order(self):
        for rec in self:
            res = self.env.ref('odoo_consignment_process.purchase_form_action_custom_consignment')
            order_ids = self.env['sale.order.line'].search([
                ('order_id', '=', rec.id),
                ('purchase_order_line_id', '!=', False)
            ])
            res = res.read()[0]
            po_order = []
            for line in order_ids:
                if line.purchase_order_line_id:
                    po_order.append(line.purchase_order_line_id.order_id.id)
            res['domain'] = str([
                ('id', '=', po_order)
            ])
        return res

#    @api.multi #odoo13
    def action_done(self):
        res = super(SaleOrder, self).action_done()
        for rec in self:
            for line in rec.order_line:
                if line.purchase_order_line_id:
                    line.product_id.write({
                        'sale_order_line_ids': [(4, line.id)],
                        # 'total_available_qty': line.product_id.total_available_qty - line.product_uom_qty,
                        # 'sale_qty': line.product_id.sale_qty + line.product_uom_qty,
                        # 'sale_price_total': line.product_id.sale_price_total + line.price_subtotal,
                    })
        return res


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    purchase_order_line_id = fields.Many2one(
        'purchase.order.line',
        string="Purchase Order Line"
    )
#     product_id = fields.Many2one(
#         domain=[('sale_ok', '=', True),('sale_state', '=', 'not_sold')]
#     )

#    @api.multi #odoo13
    # @api.onchange('product_id')
    # def product_id_change(self):
    #     res = super(SaleOrderLine, self).product_id_change()
    #     if self.product_id and self.product_id.purchase_order_line_id:
    #         self.update({
    #             'purchase_order_line_id': self.product_id.purchase_order_line_id.id
    #         })
    #     return res
