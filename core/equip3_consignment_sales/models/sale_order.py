# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from lxml import etree
import json


class SaleOrder(models.Model):
    _inherit = "sale.order"

    sale_consign = fields.Boolean("Sale Consign")
    sale_consignment_id = fields.Many2one(
        'sale.consignment.agreement', string='Consignment Agreement')

    @api.onchange('partner_id')
    def _onchange_branch_id_warehouse_id(self):
        if self.sale_consign:
            self.branch_id = self.partner_id.branch_id.id
            self.warehouse_id = self.partner_id.sale_consignment_location_id.warehouse_id.id
            self.warehouse_new_id = self.partner_id.sale_consignment_location_id.warehouse_id.id
            return {
                'domain': {'partner_id': [('is_a_consign', '=', True), ('branch_id', 'in', self.env.branches.ids), ('is_customer', '=', True), ('customer_rank', '>', 0), '|', ('company_id', '=', False), ('company_id', '=', self.env.company.id)]},
            }

    @api.onchange('branch_id', 'company_id')
    def set_warehouse_id(self):
        res = super(SaleOrder, self).set_warehouse_id()
        if self.sale_consign and self.branch_id == self.partner_id.branch_id:
            self.warehouse_id = self.partner_id.sale_consignment_location_id.warehouse_id.id
            self.warehouse_new_id = self.partner_id.sale_consignment_location_id.warehouse_id.id
        return res


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    product_tmpl_consignment_id = fields.Many2one(
        comodel_name='product.template', string='Product')
    product_consignment_id_domain = fields.Char(
        string='Product', compute="_compute_product_consignment_id_domain")

    @api.onchange('product_uom', 'product_uom_qty')
    def product_uom_change(self):
        res = super(SaleOrderLine, self).product_uom_change()
        sale_consignment_id = self.order_id.sale_consignment_id
        if not sale_consignment_id:
            return res
        if sale_consignment_id:
            price = sale_consignment_id.consignment_line_ids.filtered(
                lambda x: x.product_id.id == self.product_template_id.id).mapped('product_unit_price')
            self.price_unit = price[0] if price else 0

    @api.onchange('product_tmpl_consignment_id')
    def product_tmpl_onchange(self):
        if self.product_tmpl_consignment_id:
            self.product_template_id = self.product_tmpl_consignment_id
            self.product_id = self.env['product.product'].search(
                [('product_tmpl_id', '=', self.product_tmpl_consignment_id.id)], limit=1)
            self.location_id = self.order_id.partner_id.sale_consignment_location_id.id
            self.line_warehouse_id = self.order_id.partner_id.sale_consignment_location_id.warehouse_id.id
            self.line_warehouse_id_new = self.order_id.partner_id.sale_consignment_location_id.warehouse_id.id

    @api.depends('product_tmpl_consignment_id')
    def _compute_product_consignment_id_domain(self):

        if not self.order_id.sale_consignment_id:
            self.product_consignment_id_domain = json.dumps([('id', 'in', [])])
        else:
            product_tmpl_ids = self.env['sale.consignment.agreement'].search(
                [('id', '=', self.order_id.sale_consignment_id.id)], limit=1).consignment_line_ids.mapped('product_id')
            product_ids = self.env['product.product'].search(
                [('product_tmpl_id', 'in', product_tmpl_ids.ids)])
            existing_product_ids = self.order_id.order_line.mapped(
                'product_id').ids
            new_product_ids = [
                product_id.product_tmpl_id.id for product_id in product_ids if product_id.id not in existing_product_ids]
            domain = json.dumps([('id', 'in', new_product_ids)])
            self.product_consignment_id_domain = domain
