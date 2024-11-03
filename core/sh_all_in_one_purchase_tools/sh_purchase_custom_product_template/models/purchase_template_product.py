# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models, fields, api
from datetime import datetime

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_enable_purchase_custom_product_template = fields.Boolean(
        "Enable Purchase Custom Product Template", implied_group='sh_all_in_one_purchase_tools.group_enable_purchase_custom_product_template')


class PurchaseProductTemplateLine(models.Model):
    _name = 'purchase.product.template.line'
    _description = "Purchase Product Template Line"

    name = fields.Many2one("product.product", string="Product", required=True)
    description = fields.Char("Description")
    ordered_qty = fields.Float("Ordered Qty")
    unit_price = fields.Float("Unit Price")
    product_uom = fields.Many2one("uom.uom", string="Uom")
    purchase_template_id = fields.Many2one(
        "purchase.product.template", string="purchase Template Id")
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)

    @api.onchange('name')
    def product_change(self):
        if self.name:
            product_obj = self.env['product.product'].search(
                [('id', '=', self.name.id)])
            if product_obj:
                self.description = product_obj.display_name
                self.ordered_qty = 1
                self.unit_price = product_obj.list_price
                self.product_uom = product_obj.uom_id.id


class PurchaseProductTemplate(models.Model):
    _name = 'purchase.product.template'
    _description = "Purchase Product Template"

    name = fields.Char("Template", required=True)
    purchase_product_template_ids = fields.One2many(
        "purchase.product.template.line", "purchase_template_id", string="purchase Product Line")
    templ_active = fields.Boolean("Active", default=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    product_template_id = fields.Many2one(
        "purchase.product.template", string="Product Template")

    @api.model
    @api.onchange('product_template_id')
    def product_template_id_change(self):
        if self.product_template_id:
            self.order_line = False
            purchase_ordr_line = []
            for record in self.product_template_id.purchase_product_template_ids:
                vals = {}
                vals.update({'price_unit': record.unit_price,
                             'name': record.description, 'product_qty': record.ordered_qty, 'product_uom': record.product_uom.id, 'date_planned': datetime.now()})
                if record.name:
                    vals.update({'product_id': record.name.id})
                purchase_ordr_line.append((0, 0, vals))
            self.order_line = purchase_ordr_line
        return {'type': 'ir.actions.client', 'tag': 'reload'}
