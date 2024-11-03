# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    po_consignment_product_count = fields.Integer(
        string="PO Consignment Product Count",
        compute="_po_consignment_product_count",
    )
    so_consignment_product_count = fields.Integer(
        string="SO Consignment Product Count",
        compute="_so_consignment_product_count",
    )

    @api.depends()
    def _so_consignment_product_count(self):
        pro_ids = []
        for rec in self:
            product_ids = self.env['product.product'].search([('sale_order_line_ids', '!=', False)])
            for product in product_ids:
                for line in product.sale_order_line_ids:
                    if line.order_id.partner_id == rec:
                        if not product.id in pro_ids:
                            pro_ids.append(product.id)
            rec.so_consignment_product_count = len(pro_ids)
#             rec.so_consignment_product_count = self.env['product.product'].search_count([
#                 ('sale_order_line_id.order_id.partner_id', '=', rec.id),
#                 ('sale_order_line_id.order_id.is_consignment', '=', True)
#             ])

    @api.depends()
    def _po_consignment_product_count(self):
        for rec in self:
            # rec.po_consignment_product_count = self.env['product.product'].search_count([
            #     ('purchase_order_line_id.order_id.partner_id', '=', rec.id),
            #     ('purchase_order_line_id.order_id.is_consignment', '=', True)
            # ])
            line_ids = self.env['purchase.order.line'].search([
                ('partner_id', '=', rec.id),
                ('is_consignment', '=', True),
                ('state', 'in', ['purchase', 'done'])
            ])
            if line_ids:
                rec.po_consignment_product_count = len(list(line_ids.mapped('product_id')))
            else:
                rec.po_consignment_product_count = 0

#    @api.multi #odoo13
    def show_po_consignment_product(self):
        for rec in self:
            res = self.env.ref('product.product_normal_action_sell')
            res = res.read()[0]
            line_ids = self.env['purchase.order.line'].search([
                ('partner_id', '=', rec.id),
                ('is_consignment', '=', True),
                ('state', 'in', ['purchase', 'done'])
            ])
            domain = []
            if line_ids:
                product_ids = line_ids.mapped('product_id')
                domain = [('id', 'in', product_ids.ids)]
            res['domain'] = str(domain)
        return res

#    @api.multi #odoo13
    def show_so_consignment_product(self):
        pro_ids = []
        for rec in self:
            res = self.env.ref('product.product_normal_action_sell')
            res = res.read()[0]
            product_ids = self.env['product.product'].search([('sale_order_line_ids', '!=', False)])
            for product in product_ids:
                for line in product.sale_order_line_ids:
                    if line.order_id.partner_id == rec:
                        pro_ids.append(product.id)
            res['domain'] = str([
                ('id', 'in', pro_ids),
            ])
        return res
